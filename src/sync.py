"""Article-level delta synchronization with resumable replacement transactions."""

import hashlib
import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from openai import NotFoundError

from src.provider import STRATEGY, save_json

LOGGER = logging.getLogger(__name__)


@contextmanager
def state_lock(directory):
    """OS-owned lock is released even if the process crashes."""
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'sync.lock').open('a+b') as handle:
        handle.seek(0)
        if handle.read(1) == b'':
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if __import__('os').name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError('Another sync process is using this state directory.') from None
        try:
            yield
        finally:
            handle.seek(0)
            if __import__('os').name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def synchronize(knowledge):
    with state_lock(knowledge.settings.state_dir):
        # Reload under lock: a previous process may have finished meanwhile.
        if knowledge.path.exists():
            knowledge.state = json.loads(knowledge.path.read_text(encoding='utf-8'))
        return _synchronize(knowledge)


def _synchronize(k):
    state, settings, client = k.state, k.settings, k.client
    report = json.loads((settings.data_dir / 'scrape-report.json').read_text(encoding='utf-8'))
    if len(report['articles']) < settings.article_limit:
        raise ValueError('Scrape report has fewer articles than configured.')
    if state.get('schema_version') != 2 or state.get('ingestion_strategy') != 'whole_article_v1':
        raise ValueError('Incompatible state schema. Use the matching state directory.')
    prepared = {}
    for item in report['articles']:
        article_id = str(item['id'])
        path = (settings.data_dir / item['file']).resolve()
        if path.parent != settings.data_dir.resolve() or article_id in prepared:
            raise ValueError('Invalid or duplicate article in scrape report.')
        text = path.read_text(encoding='utf-8').replace('\r\n', '\n')
        if not text.strip():
            raise ValueError('Article has no content.')
        if len(text.encode('utf-8')) > 16 * 1024 * 1024:
            raise ValueError('Article exceeds the application upload limit of 16 MiB.')
        prepared[article_id] = {'sha256': hashlib.sha256(text.encode()).hexdigest(),
                                'content': text, 'filename': f'{article_id}.md'}
    if not state.get('vector_store_id'):
        state['vector_store_id'] = client.vector_stores.create(name='Nimbus 47 Articles', expires_after={'anchor': 'last_active_at', 'days': 7}).id
        save_json(k.path, state)
    store_id = state['vector_store_id']
    counts = {'added': 0, 'updated': 0, 'skipped': 0}
    uploaded = 0
    # Finish interrupted transactions first, including articles not selected this run.
    ids = list(dict.fromkeys([*state.get('pending', {}), *prepared]))
    for article_id in ids:
        old = state['articles'].get(article_id)
        doc = prepared.get(article_id)
        transaction = state['pending'].get(article_id)
        if not transaction:
            if old and old['sha256'] == doc['sha256'] and old.get('ingestion_strategy') == 'whole_article_v1':
                counts['skipped'] += 1
                continue
            transaction = {'sha256': doc['sha256'], 'filename': doc['filename'], 'content': doc['content'], 'files': {},
                           'kind': 'updated' if old else 'added', 'ready': False,
                           'old_files': list(old['files'].values()) if old else []}
            state['pending'][article_id] = transaction
            save_json(k.path, state)
        name = transaction['filename']
        content = transaction['content']
        if name not in transaction['files']:
            remote = client.files.create(file=(name, content.encode(), 'text/markdown'), purpose='assistants')
            transaction['files'][name] = {'id': remote.id, 'sha256': hashlib.sha256(content.encode()).hexdigest(), 'indexed': False}
            uploaded += 1
            save_json(k.path, state)
        if not transaction['ready']:
            if not transaction.get('batch_id'):
                transaction['batch_id'] = client.vector_stores.file_batches.create(vector_store_id=store_id,
                    file_ids=[f['id'] for f in transaction['files'].values()], chunking_strategy=STRATEGY).id
                save_json(k.path, state)
            deadline = time.monotonic() + 600
            while True:
                batch = client.vector_stores.file_batches.retrieve(transaction['batch_id'], vector_store_id=store_id)
                if batch.status != 'in_progress':
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('Indexing timeout; transaction saved for retry.')
                time.sleep(3)
            if batch.status != 'completed' or batch.file_counts.failed or batch.file_counts.cancelled:
                # Permit a fresh indexing attempt with the same uploaded IDs on retry.
                transaction.pop('batch_id', None)
                save_json(k.path, state)
                raise ValueError('Indexing failed; old article remains active.')
            transaction['ready'] = True
            for record in transaction['files'].values():
                record['indexed'] = True
            save_json(k.path, state)
        # Detach the previous article file only after replacement indexing succeeds.
        while transaction['old_files']:
            record = transaction['old_files'][0]
            try:
                client.vector_stores.files.delete(record['id'], vector_store_id=store_id)
            except NotFoundError:
                pass  # Previous attempt may have detached it before a crash.
            transaction['old_files'].pop(0)
            save_json(k.path, state)
        state['articles'][article_id] = {'sha256': transaction['sha256'], 'ingestion_strategy': 'whole_article_v1', 'files': transaction['files']}
        counts[transaction['kind']] += 1
        del state['pending'][article_id]
        state['files'] = {n: f for a in state['articles'].values() for n, f in a['files'].items()}
        save_json(k.path, state)
        LOGGER.info('Article synced: id=%s action=%s', article_id, transaction['kind'])
        # If the source changed again during a resumed transaction, rerun rather
        # than silently report a newer local version as synchronized.
        if doc and doc['sha256'] != transaction['sha256']:
            raise ValueError('Recovered an earlier version; run sync again for the latest source.')
    store = client.vector_stores.retrieve(store_id)
    summary = {'completed_at': datetime.now(timezone.utc).isoformat(), 'vector_store_id': store_id,
               **counts, 'uploaded_files': uploaded, 'source_articles': len(prepared),
               'indexed_files': len(state['files']), 'provider_file_counts': store.file_counts.model_dump(),
               'usage_bytes': store.usage_bytes, 'chunking_strategy': STRATEGY,
               'count_note': 'One Markdown file per article; OpenAI performs chunking and embedding. Internal chunk total is not exposed.'}
    save_json(settings.state_dir / 'sync-report.json', summary)
    save_json(settings.state_dir / 'upload-report.json', summary)
    LOGGER.info('Sync complete: added=%d updated=%d skipped=%d uploaded_files=%d', counts['added'], counts['updated'], counts['skipped'], uploaded)
    return summary
