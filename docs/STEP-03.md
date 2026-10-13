# Step 3: Collect 50 English Articles

```powershell
cd C:\workspace\prepare-interview\projects\nimbus-47
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --scrape-only
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Set `ARTICLE_LIMIT=50` in `.env`. The sample and code default also use 50. Shell environment variables take precedence.

## Pipeline

1. Find the YouTube guide through Zendesk Search and fetch its full English article body.
2. Fetch the en-us Articles endpoint in pages of 25, following `next_page`.
3. Exclude drafts, empty content, non-English articles and duplicate IDs. Stop at 50; fail if insufficient articles are available.
4. Remove script, style, navigation, aside, footer and advertisement elements with BeautifulSoup. Article bodies from the API exclude the surrounding website layout.
5. Convert to Markdown with headings, fenced code, relative links and images preserved.
6. Save `data/articles/<id>-<slug>.md`, including `Article URL:`, and `scrape-report.json`.

Requests use a 10-second connection timeout and a 30-second read timeout. Up to three retries cover connection errors, HTTP 429 and selected 5xx responses. Backoff and Retry-After delays are bounded. HTTP, JSON and output errors exit with code one.

The dataset includes YouTube plus alphabetically selected articles; it is not comprehensive product coverage. This command does not call an AI service. The uploader reads the report rather than blindly uploading stale files in the output directory. Delta synchronization and daily deployment are later steps.

API reference: https://developer.zendesk.com/api-reference/help_center/help-center-api/articles/
