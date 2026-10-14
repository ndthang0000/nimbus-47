# Step 4: API Upload and File Search

## Commands

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --upload-only
.\.venv\Scripts\python.exe main.py --ask "How do I add a YouTube video?"
```

These commands use `API_KEY` from the environment. Model calls are billable. The default model is `gpt-5.4-mini`; override it with `OPENAI_MODEL`. The key needs Files, Vector Stores and Responses access in the same project.

## Exact Required Prompt

You are OptiBot, the customer-support bot for OptiSigns.com. â€¢ Tone: helpful, factual, concise. â€¢ Only answer using the uploaded docs. â€¢ Max 5 bullet points; else link to the doc. â€¢ Cite up to 3 "Article URL:" lines per reply.

## Upload and Indexing

- Read the dataset from scrape-report.json and upload one full Markdown file per article, named by article ID.
- Validate nonempty content and the application limit of 16 MiB before upload. Provider token limits can still reject unusually large files.
- Attach files using a vector-store batch with static 4096-token chunking and zero overlap. OpenAI handles chunking, embeddings and indexing.
- Report source_articles, uploaded_files, indexed_files and provider_file_counts. Internal embedding chunk totals are not exposed.
- Persist uploaded IDs and batch progress, then mark indexed only after completion without failed/cancelled files.
- Store expiration: seven inactive days. Delta updates use article-level hashes and a versioned ingestion strategy.

## Artifacts

| File | Contents |
|---|---|
| `state/openai.json` | Store ID, remote file IDs and indexing state; no API key |
| `state/upload-report.json` | Article/file counts, provider counts, storage bytes and provider chunking strategy |
| `state/last-answer.json` | Response, retrieval results, citations and token usage |
| `state/last-answer.md` | Demo question and answer |

Each of the 50 source articles is represented by one indexed Markdown file.

## Remaining UI Evidence

Assistants API was retired on August 26, 2026. The implementation uses Responses and File Search. In the current Platform UI, save a Prompt using the exact instructions and connect File Search to the store ID from the report in the same project.

If the UI cannot support the required demo, clarify an equivalent demonstration with HR. Ask the YouTube question in the UI and capture the answer with citations. The CLI demonstration proves backend behavior but does not replace the required UI screenshot.

## References

- https://developers.openai.com/api/docs/assistants/migration
- https://developers.openai.com/api/docs/guides/tools-file-search
- https://developers.openai.com/api/reference/resources/vector_stores/subresources/file_batches/methods/create
