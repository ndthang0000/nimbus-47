"""Validate local runtime configuration."""

import argparse
import logging

from src.config import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description='Nimbus 47 ingestion job')
    parser.add_argument('--check-config', action='store_true', help='Validate configuration without network requests')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    try:
        settings = load_settings()
    except ValueError as error:
        logging.error('%s', error)
        return 1
    if args.check_config:
        logging.info('Configuration valid: provider=%s article_limit=%d', settings.provider, settings.article_limit)
        logging.info('API key present; credentials have not been verified with the provider.')
        return 0
    logging.error('Choose --check-config.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
