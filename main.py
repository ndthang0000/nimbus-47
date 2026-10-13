"""Entrypoint for configuration, scraping, ingestion and demo questions."""

import argparse
import logging
import json
from datetime import datetime, timezone

import requests

from src.config import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description='Nimbus 47 ingestion job')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--check-config', action='store_true', help='Validate configuration without network requests')
    actions.add_argument('--scrape-only', action='store_true', help='Download English articles as Markdown; no AI API calls')
    actions.add_argument('--upload-only', action='store_true', help='Upload/index the existing scrape dataset via OpenAI API')
    actions.add_argument('--ask', metavar='QUESTION', help='Ask using Responses API and File Search (billable)')
    actions.add_argument('--sync', action='store_true', help='Re-scrape and synchronize new/updated articles')
    args = parser.parse_args()
    try:
        settings = load_settings()
    except ValueError as error:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
        logging.error('%s', error)
        return 1
    logging.basicConfig(level=settings.log_level, format='%(asctime)s %(levelname)s %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    if args.upload_only or args.ask:
        from openai import OpenAIError
        from src.provider import KnowledgeBase
        try:
            knowledge = KnowledgeBase(settings)
            if args.upload_only:
                knowledge.upload()
            else:
                print(knowledge.ask(args.ask))
            return 0
        except (OpenAIError, ValueError, OSError, KeyError, TimeoutError) as error:
            logging.error('OpenAI operation failed (%s); HTTP status=%s. Check billing, API permissions, input files and saved state.', type(error).__name__, getattr(error, 'status_code', 'n/a'))
            return 1
    if args.check_config:
        logging.info('Configuration valid: provider=%s article_limit=%d', settings.provider, settings.article_limit)
        logging.info('API key present; credentials have not been verified with the provider.')
        return 0
    if args.scrape_only or args.sync:
        from src.scraper import ZendeskScraper
        from src.markdown import article_filename, article_markdown
        scraper = ZendeskScraper(settings.help_center_url)
        try:
            articles = scraper.collect(settings.article_limit)
            # Convert everything before writing: conversion errors fail the run.
            documents = [(article, article_filename(article), article_markdown(article)) for article in articles]
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            records = []
            for article, filename, content in documents:
                target = settings.data_dir / filename
                temporary = target.with_suffix('.md.tmp')
                temporary.write_text(content, encoding='utf-8')
                temporary.replace(target)
                records.append({'id': article['id'], 'title': article['title'], 'url': article['html_url'],
                                'updated_at': article.get('updated_at'), 'file': filename})
            report = {'completed_at': datetime.now(timezone.utc).isoformat(), 'count': len(records), 'articles': records}
            (settings.data_dir / 'scrape-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            logging.info('Scrape complete: saved=%d directory=%s; no AI upload performed', len(records), settings.data_dir)
            if args.sync:
                from openai import OpenAIError
                from src.provider import KnowledgeBase
                try:
                    KnowledgeBase(settings).upload()
                except (OpenAIError, ValueError, OSError, KeyError, TimeoutError) as error:
                    logging.error('Sync failed (%s); saved state can be retried.', type(error).__name__)
                    return 1
            return 0
        except (requests.RequestException, ValueError, KeyError, OSError) as error:
            logging.error('Scrape failed (%s). Check network/API response and output permissions.', type(error).__name__)
            return 1
        finally:
            scraper.close()
    logging.error('Choose --check-config, --scrape-only, --upload-only, --sync or --ask.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
