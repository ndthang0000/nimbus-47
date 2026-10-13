import unittest
from unittest.mock import patch

from src.markdown import article_markdown
from src.scraper import ZendeskScraper


def article(identifier=1, title='Sample'):
    return {'id': identifier, 'title': title, 'locale': 'en-us', 'draft': False,
            'body': '<p>Content</p>', 'html_url': 'https://example.com/article'}


class IngestionTests(unittest.TestCase):
    def test_markdown_preserves_semantics(self):
        item = article()
        item['body'] = '<nav>REMOVE NAV</nav><h2>Setup</h2><a href="../other">Guide</a><pre><code>x = 1\nprint(x)</code></pre><script>REMOVE SCRIPT</script>'
        result = article_markdown(item)
        self.assertIn('## Setup', result)
        self.assertIn('[Guide](../other)', result)
        self.assertIn('```', result)
        self.assertIn('x = 1\nprint(x)', result)
        self.assertNotIn('REMOVE', result)

    def test_pagination_deduplicates_and_filters(self):
        client = ZendeskScraper('https://example.com')
        foreign = article(8)
        foreign['locale'] = 'fr'
        with patch.object(client, 'get_json', side_effect=[
            {'results': [article(1, 'YouTube')]}, {'article': article(1, 'YouTube')},
            {'articles': [article(1), foreign, article(2)], 'next_page': '/page2'},
            {'articles': [article(3)], 'next_page': None},
        ]) as get:
            result = client.collect(3)
        self.assertEqual([a['id'] for a in result], [1, 2, 3])
        self.assertEqual(get.call_count, 4)
        client.close()

    def test_insufficient_articles_fails(self):
        client = ZendeskScraper('https://example.com')
        with patch.object(client, 'get_json', side_effect=[
            {'results': [article(1, 'YouTube')]}, {'article': article(1, 'YouTube')},
            {'articles': [], 'next_page': None},
        ]):
            with self.assertRaisesRegex(ValueError, 'requested 50'):
                client.collect(50)
        client.close()

    def test_http_error_is_not_silently_ignored(self):
        import requests
        client = ZendeskScraper('https://example.com')
        with patch.object(client.session, 'get') as get:
            get.return_value.raise_for_status.side_effect = requests.HTTPError('404')
            with self.assertRaises(requests.HTTPError):
                client.get_json('/missing')
            self.assertEqual(get.call_args.kwargs['timeout'], (10, 30))
        client.close()


if __name__ == '__main__':
    unittest.main()
