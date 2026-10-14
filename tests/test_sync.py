import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.provider import KnowledgeBase


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.settings = SimpleNamespace(provider='openai', api_key='test', state_dir=root/'state', data_dir=root/'data', article_limit=1)
        self.settings.data_dir.mkdir()
        self.client = MagicMock()
        self.client.vector_stores.create.return_value.id = 'vs_test'
        self.client.files.create.side_effect = [SimpleNamespace(id=f'file_{i}') for i in range(30)]
        self.client.vector_stores.file_batches.create.return_value.id = 'batch_test'
        self.client.vector_stores.file_batches.retrieve.return_value = SimpleNamespace(status='completed', file_counts=SimpleNamespace(failed=0, cancelled=0))
        self.client.vector_stores.retrieve.return_value = SimpleNamespace(usage_bytes=123, file_counts=SimpleNamespace(model_dump=lambda: {'completed': 1}))
        self.write('Original')

    def tearDown(self):
        self.temp.cleanup()

    def write(self, body, filename='1-one.md', identifier=1):
        (self.settings.data_dir/filename).write_text(f'# One\n\nArticle URL: https://example.com\n\n{body}', encoding='utf-8')
        (self.settings.data_dir/'scrape-report.json').write_text(json.dumps({'articles': [{'id': identifier, 'file': filename}]}))

    def run_sync(self):
        return KnowledgeBase(self.settings, client=self.client).upload()

    def test_added_then_unchanged_does_not_upload(self):
        self.assertEqual(self.run_sync()['added'], 1)
        self.client.reset_mock()
        report = self.run_sync()
        self.assertEqual(report['skipped'], 1)
        self.client.files.create.assert_not_called()
        self.client.vector_stores.file_batches.create.assert_not_called()

    def test_rename_and_shrink_replaces_article(self):
        self.write('Long text. ' * 6000)
        self.run_sync()
        old_count = self.client.files.create.call_count
        self.assertEqual(old_count, 1)
        self.client.reset_mock()
        self.write('Short changed text', filename='1-renamed.md')
        result = self.run_sync()
        self.assertEqual(result['updated'], 1)
        self.assertEqual(result['uploaded_files'], 1)
        self.assertEqual(self.client.vector_stores.files.delete.call_count, old_count)
        self.assertEqual(result['indexed_files'], 1)

    def test_failed_indexing_retains_old_and_retry_reuses_upload(self):
        self.run_sync()
        old_hash = KnowledgeBase(self.settings, self.client).state['articles']['1']['sha256']
        self.write('Changed')
        self.client.vector_stores.file_batches.retrieve.return_value.status = 'failed'
        with self.assertRaises(ValueError):
            self.run_sync()
        state = KnowledgeBase(self.settings, self.client).state
        self.assertEqual(state['articles']['1']['sha256'], old_hash)
        self.assertFalse(state['pending']['1']['ready'])
        self.client.vector_stores.files.delete.assert_not_called()
        self.client.reset_mock()
        self.client.vector_stores.file_batches.retrieve.return_value.status = 'completed'
        self.assertEqual(self.run_sync()['updated'], 1)
        self.client.files.create.assert_not_called()

    def test_cleanup_failure_resumes_without_reupload(self):
        self.run_sync()
        self.write('Changed')
        self.client.vector_stores.files.delete.side_effect = RuntimeError('network interruption')
        with self.assertRaises(RuntimeError):
            self.run_sync()
        self.assertTrue(KnowledgeBase(self.settings, self.client).state['pending']['1']['ready'])
        self.client.reset_mock()
        self.client.vector_stores.files.delete.side_effect = None
        self.assertEqual(self.run_sync()['updated'], 1)
        self.client.files.create.assert_not_called()
        self.client.vector_stores.file_batches.create.assert_not_called()

    def test_state_strategy_mismatch_is_rejected(self):
        self.run_sync()
        k = KnowledgeBase(self.settings, self.client)
        k.state['ingestion_strategy'] = 'unsupported'
        from src.provider import save_json
        save_json(k.path, k.state)
        self.client.reset_mock()
        with self.assertRaisesRegex(ValueError, 'Incompatible state'):
            self.run_sync()
        self.client.files.create.assert_not_called()

    def test_same_hash_with_different_article_strategy_is_reindexed(self):
        self.run_sync()
        k = KnowledgeBase(self.settings, self.client)
        k.state['articles']['1']['ingestion_strategy'] = 'unsupported'
        from src.provider import save_json
        save_json(k.path, k.state)
        self.client.reset_mock()
        self.assertEqual(self.run_sync()['updated'], 1)
        self.client.files.create.assert_called_once()

    def test_new_selection_does_not_delete_omitted_articles(self):
        self.run_sync()
        self.write('Second article', filename='2-two.md', identifier=2)
        self.assertEqual(self.run_sync()['added'], 1)
        self.client.vector_stores.files.delete.assert_not_called()
        self.assertEqual(len(KnowledgeBase(self.settings, self.client).state['articles']), 2)


if __name__ == '__main__':
    unittest.main()
