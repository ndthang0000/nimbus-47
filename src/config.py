"""Load and validate configuration without exposing credentials."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    provider: str
    api_key: str = field(repr=False)
    help_center_url: str
    article_limit: int
    data_dir: Path
    state_dir: Path
    log_level: str


def load_settings() -> Settings:
    # Cloud/container environment takes precedence over local .env.
    load_dotenv(ROOT / '.env', override=False)
    provider = os.getenv('AI_PROVIDER', '').strip().lower()
    if provider not in {'openai', 'gemini'}:
        raise ValueError('AI_PROVIDER must be openai or gemini.')
    api_key = os.getenv('API_KEY', '').strip()
    if not api_key:
        raise ValueError('API_KEY is required. Set it in .env or the environment.')
    try:
        limit = int(os.getenv('ARTICLE_LIMIT', '50'))
    except ValueError:
        raise ValueError('ARTICLE_LIMIT must be an integer.') from None
    if limit < 30:
        raise ValueError('ARTICLE_LIMIT must be at least 30.')
    url = os.getenv('HELP_CENTER_URL', 'https://support.optisigns.com').strip()
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('HELP_CENTER_URL must be an HTTPS URL without credentials.')
    level = os.getenv('LOG_LEVEL', 'INFO').strip().upper()
    if level not in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}:
        raise ValueError('LOG_LEVEL is invalid.')
    return Settings(
        provider=provider,
        api_key=api_key,
        help_center_url=url.rstrip('/'),
        article_limit=limit,
        data_dir=ROOT / os.getenv('DATA_DIR', 'data/articles'),
        state_dir=ROOT / os.getenv('STATE_DIR', 'state'),
        log_level=level,
    )
