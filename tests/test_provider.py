import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import tiktoken

from src.provider import KnowledgeBase, split_document


class ProviderTests(unittest.TestCase):
    def test_chunks_preserve_unicode_and_source(self):
        prefix = '# Example\n\nArticle URL: https://example.com\n\n'
        body = ('Unicode café 🐈 and Markdown `code`.\n\n' * 1200)
        chunks = split_document(prefix + body)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(''.join(c[len(prefix):] for c in chunks), body)
        encoding = tiktoken.get_encoding('cl100k_base')
        self.assertTrue(all(len(encoding.encode(c)) <= 3000 for c in chunks))
        self.assertTrue(all(c.startswith(prefix) for c in chunks))

    def test_failed_indexing_does_not_mark_synced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / 'data'
            data.mkdir()
            (data / 'one.md').write_text('# One\n\nArticle URL: https://example.com\n\nHello', encoding='utf-8')
            (data / 'scrape-report.json').write_text(json.dumps({'articles': [{'file': 'one.md'}]}))
            settings = SimpleNamespace(provider='openai', api_key='test', state_dir=root / 'state', data_dir=data, article_limit=1)
            client = MagicMock()
            client.vector_stores.create.return_value.id = 'vs_test'
            client.files.create.return_value.id = 'file_test'
            client.vector_stores.file_batches.create.return_value.id = 'batch_test'
            client.vector_stores.file_batches.retrieve.return_value = SimpleNamespace(status='failed', file_counts=SimpleNamespace(completed=0, failed=1, cancelled=0))
            loader = KnowledgeBase(settings, client=client)
            with self.assertRaisesRegex(ValueError, 'Indexing failed'):
                loader.upload()
            saved = json.loads(loader.path.read_text())
            self.assertFalse(saved['files']['one-part-1.md']['indexed'])
            self.assertEqual(saved['batch_id'], 'batch_test')


if __name__ == '__main__':
    unittest.main()
