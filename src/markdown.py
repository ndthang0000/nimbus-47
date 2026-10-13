"""Normalize article bodies; preserve relative links and fenced code."""

import re
from bs4 import BeautifulSoup
from markdownify import markdownify


def article_markdown(article: dict) -> str:
    soup = BeautifulSoup(article['body'], 'html.parser')
    for element in soup.select('script, style, nav, aside, footer, .advertisement, .ads'):
        element.decompose()
    body = markdownify(str(soup), heading_style='ATX', strip=['span'], code_language='text').strip()
    if not body:
        raise ValueError(f"Empty Markdown for article {article['id']}")
    title = article['title'].replace('\n', ' ').strip()
    return f"# {title}\n\nArticle URL: {article['html_url']}\n\n{body}\n"


def article_filename(article: dict) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', article['title'].lower()).strip('-')[:100] or 'article'
    return f"{article['id']}-{slug}.md"
