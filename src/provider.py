"""OpenAI ingestion and grounded Responses API demo."""

import json
import logging
import os
from pathlib import Path

from openai import OpenAI

PROMPT = 'You are OptiBot, the customer-support bot for OptiSigns.com. • Tone: helpful, factual, concise. • Only answer using the uploaded docs. • Max 5 bullet points; else link to the doc. • Cite up to 3 "Article URL:" lines per reply.'
LOGGER = logging.getLogger(__name__)
STRATEGY = {'type': 'static', 'static': {'max_chunk_size_tokens': 4096, 'chunk_overlap_tokens': 0}}


def save_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


class KnowledgeBase:
    def __init__(self, settings, client=None):
        if settings.provider != 'openai':
            raise ValueError('This implementation supports OpenAI only.')
        self.settings = settings
        self.client = client or OpenAI(api_key=settings.api_key, timeout=60, max_retries=2)
        self.path = settings.state_dir / 'openai.json'
        self.state = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'schema_version': 2, 'ingestion_strategy': 'whole_article_v1', 'files': {}, 'articles': {}, 'pending': {}}
        if self.state.get('schema_version') != 2 or self.state.get('ingestion_strategy') != 'whole_article_v1':
            raise ValueError('Incompatible state schema. Use the matching state directory.')

    def upload(self):
        from src.sync import synchronize
        return synchronize(self)

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
