"""OpenAI ingestion and grounded Responses API demo."""

import hashlib
import json
import logging
import os
import time
from pathlib import Path

import tiktoken
from openai import OpenAI

PROMPT = 'You are OptiBot, the customer-support bot for OptiSigns.com. • Tone: helpful, factual, concise. • Only answer using the uploaded docs. • Max 5 bullet points; else link to the doc. • Cite up to 3 "Article URL:" lines per reply.'
LOGGER = logging.getLogger(__name__)
STRATEGY = {'type': 'static', 'static': {'max_chunk_size_tokens': 4096, 'chunk_overlap_tokens': 0}}


def save_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def split_document(text: str) -> list[str]:
    """Bounded character slices preserve Unicode; repeat source/title per part."""
    encoding = tiktoken.get_encoding('cl100k_base')
    header, body = text.split('\n\n', 2)[0:2], text.split('\n\n', 2)[2]
    prefix = '\n\n'.join(header) + '\n\n'
    chunks = []
    while body:
        low, high = 1, len(body)
        while low < high:
            midpoint = (low + high + 1) // 2
            if len(encoding.encode(prefix + body[:midpoint], disallowed_special=())) <= 3000:
                low = midpoint
            else:
                high = midpoint - 1
        end = low
        if end < len(body):
            paragraph = body.rfind('\n\n', 0, end)
            if paragraph > end // 2:
                end = paragraph + 2
        chunk = prefix + body[:end]
        if len(encoding.encode(chunk, disallowed_special=())) > 3000:
            raise ValueError('Document header exceeds chunk budget.')
        chunks.append(chunk)
        body = body[end:]
    return chunks


class KnowledgeBase:
    def __init__(self, settings, client=None):
        if settings.provider != 'openai':
            raise ValueError('This implementation supports OpenAI only.')
        self.settings = settings
        self.client = client or OpenAI(api_key=settings.api_key, timeout=60, max_retries=2)
        self.path = settings.state_dir / 'openai.json'
        self.state = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'files': {}}

    def upload(self):
        from src.sync import synchronize
        if self.state.get('batch_id'):
            self._legacy_upload()
        return synchronize(self)

    def _legacy_upload(self):
        report = json.loads((self.settings.data_dir / 'scrape-report.json').read_text(encoding='utf-8'))
        if len(report['articles']) < self.settings.article_limit:
            raise ValueError('Scrape report has fewer articles than configured.')
        documents = []
        for item in report['articles']:
            file = (self.settings.data_dir / item['file']).resolve()
            if file.parent != self.settings.data_dir.resolve():
                raise ValueError('Invalid report file path.')
            for index, content in enumerate(split_document(file.read_text(encoding='utf-8')), 1):
                name = f"{file.stem}-part-{index}.md"
                digest = hashlib.sha256(content.encode()).hexdigest()
                old = self.state['files'].get(name)
                if old and old['sha256'] != digest:
                    raise ValueError('Document changed; replacement sync is implemented in step 5, not this initial loader.')
                documents.append((name, content, digest))
        if not self.state.get('vector_store_id'):
            store = self.client.vector_stores.create(name='Nimbus 47 knowledge', expires_after={'anchor': 'last_active_at', 'days': 7})
            self.state['vector_store_id'] = store.id
            save_json(self.path, self.state)
        store_id = self.state['vector_store_id']
        # Save remote IDs after each upload so an interrupted run can resume.
        for name, content, digest in documents:
            if name not in self.state['files']:
                remote = self.client.files.create(file=(name, content.encode(), 'text/markdown'), purpose='assistants')
                self.state['files'][name] = {'id': remote.id, 'sha256': digest, 'indexed': False}
                save_json(self.path, self.state)
                LOGGER.info('Uploaded chunk file: %s', name)
        pending = [self.state['files'][name]['id'] for name, _, _ in documents if not self.state['files'][name]['indexed']]
        if pending:
            batch_id = self.state.get('batch_id')
            if not batch_id:
                batch = self.client.vector_stores.file_batches.create(vector_store_id=store_id, file_ids=pending, chunking_strategy=STRATEGY)
                batch_id = batch.id
                self.state['batch_id'] = batch_id
                save_json(self.path, self.state)
            deadline = time.monotonic() + 600
            while True:
                batch = self.client.vector_stores.file_batches.retrieve(batch_id, vector_store_id=store_id)
                LOGGER.info('Indexing: status=%s completed=%d failed=%d', batch.status, batch.file_counts.completed, batch.file_counts.failed)
                if batch.status != 'in_progress':
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('Indexing timeout; rerun --upload-only to resume.')
                time.sleep(3)
            if batch.status != 'completed' or batch.file_counts.failed or batch.file_counts.cancelled:
                raise ValueError('Indexing failed; inspect the saved batch in OpenAI dashboard.')
            for record in self.state['files'].values():
                if record['id'] in pending:
                    record['indexed'] = True
            self.state.pop('batch_id', None)
            save_json(self.path, self.state)
        store = self.client.vector_stores.retrieve(store_id)
        summary = {'vector_store_id': store_id, 'source_articles': len(report['articles']),
                   'prepared_chunks': len(documents), 'indexed_chunk_files': sum(self.state['files'][n]['indexed'] for n, _, _ in documents),
                   'provider_file_counts': store.file_counts.model_dump(), 'usage_bytes': store.usage_bytes,
                   'chunking_strategy': STRATEGY,
                   'count_note': 'Local chunks <=3000 cl100k tokens, uploaded individually. Provider uses 4096-token chunks without overlap; internal embedding chunk count is not exposed.'}
        save_json(self.settings.state_dir / 'upload-report.json', summary)
        LOGGER.info('Upload complete: source_articles=%d prepared_chunks=%d indexed_chunk_files=%d storage_bytes=%d store=%s',
                    summary['source_articles'], summary['prepared_chunks'], summary['indexed_chunk_files'], store.usage_bytes, store_id)
        return summary

    def ask(self, question: str):
        store_id = self.state.get('vector_store_id')
        if self.state.get('pending') or not store_id or not self.state['files'] or not all(f['indexed'] for f in self.state['files'].values()):
            raise ValueError('Upload/index documents successfully before asking.')
        response = self.client.responses.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-5.4-mini'), instructions=PROMPT,
            input=question, tools=[{'type': 'file_search', 'vector_store_ids': [store_id], 'max_num_results': 5}],
            tool_choice='required', max_output_tokens=1800, include=['file_search_call.results'],
        )
        if response.status != 'completed' or not response.output_text:
            raise ValueError('Response incomplete; inspect token limit/model configuration.')
        save_json(self.settings.state_dir / 'last-answer.json', response.model_dump(mode='json'))
        answer = f'# Demo answer\n\nQuestion: {question}\n\n{response.output_text}\n'
        (self.settings.state_dir / 'last-answer.md').write_text(answer, encoding='utf-8')
        LOGGER.info('Response complete: model=%s input_tokens=%s output_tokens=%s', response.model, response.usage.input_tokens, response.usage.output_tokens)
        return response.output_text
