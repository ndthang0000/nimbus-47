"""Read public English Zendesk articles with pagination and bounded retries."""

import logging
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)


class ZendeskScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        retry = Retry(total=3, connect=3, read=3, status=3, backoff_factor=1,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=['GET'], respect_retry_after_header=True,
                      backoff_max=30, retry_after_max=60)
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        self.session.headers.update({'User-Agent': 'Nimbus47-Assessment/1.0', 'Accept': 'application/json'})

    def close(self):
        self.session.close()

    def get_json(self, url: str) -> dict:
        url = urljoin(self.base_url + '/', url)
        if urlparse(url).scheme != 'https' or urlparse(url).netloc != urlparse(self.base_url).netloc:
            raise ValueError('Unexpected API pagination host.')
        response = self.session.get(url, timeout=(10, 30))
        response.raise_for_status()
        return response.json()

    @staticmethod
    def eligible(article: dict) -> bool:
        return (article.get('locale', '').lower().startswith('en')
                and not article.get('draft') and bool(article.get('body'))
                and bool(article.get('title')) and bool(article.get('html_url')))

    def collect(self, limit: int) -> list[dict]:
        # Seed via search, then fetch full bodies. Ensure a relevant YouTube article
        # even when the alphabetical first pages do not contain one.
        search = self.get_json('/api/v2/help_center/articles/search.json?query=YouTube&locale=en-us&per_page=100')
        candidates = [a for a in search.get('results', []) if 'youtube' in a.get('title', '').lower()]
        candidates.sort(key=lambda a: (a.get('title', '').lower() not in {'youtube', 'youtube app'}, a['id']))
        selected = {}
        for candidate in candidates:
            article = self.get_json(f"/api/v2/help_center/en-us/articles/{candidate['id']}.json")['article']
            if self.eligible(article):
                selected[article['id']] = article
                LOGGER.info('YouTube article selected: id=%s title=%s', article['id'], article['title'])
                break
        if not selected:
            raise ValueError('No published English YouTube article found.')
        url = '/api/v2/help_center/en-us/articles.json?per_page=25&sort_by=title&sort_order=asc'
        visited = set()
        page = 0
        while url and len(selected) < limit:
            if url in visited:
                raise ValueError('Repeated pagination link detected.')
            visited.add(url)
            payload = self.get_json(url)
            page += 1
            for article in payload['articles']:
                if self.eligible(article):
                    selected.setdefault(article['id'], article)
                if len(selected) >= limit:
                    break
            LOGGER.info('Fetched page=%d selected=%d target=%d', page, len(selected), limit)
            url = payload.get('next_page')
        if len(selected) < limit:
            raise ValueError(f'Only {len(selected)} eligible articles found; requested {limit}.')
        return list(selected.values())
