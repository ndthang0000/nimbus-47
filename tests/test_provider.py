import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from src.provider import KnowledgeBase

class ProviderTests(unittest.TestCase):
    def test_full_unicode_document_uploaded_without_splitting(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / 'data'
            data.mkdir()
            text = '# Example\n\nArticle URL: https://example.com\n\n' + ('Unicode café and `code`.\n\n' * 5000)
            (data / 'article.md').write_text(text, encoding='utf-8')
            (data / 'scrape-report.json').write_text(json.dumps({'articles': [{'id': 1, 'file': 'article.md'}]}))
            settings = SimpleNamespace(provider='openai', api_key='test', state_dir=root/'state', data_dir=data, article_limit=1)
            client = MagicMock()
            client.vector_stores.create.return_value.id = 'vs_test'
            client.files.create.return_value.id = 'file_test'
            client.vector_stores.file_batches.create.return_value.id = 'batch_test'
            client.vector_stores.file_batches.retrieve.return_value = SimpleNamespace(status='completed', file_counts=SimpleNamespace(failed=0, cancelled=0))
            client.vector_stores.retrieve.return_value = SimpleNamespace(usage_bytes=123, file_counts=SimpleNamespace(model_dump=lambda: {'completed': 1}))
            result = KnowledgeBase(settings, client).upload()
            client.files.create.assert_called_once()
            self.assertEqual(client.files.create.call_args.kwargs['file'], ('1.md', text.encode(), 'text/markdown'))
            self.assertEqual(result['indexed_files'], 1)
