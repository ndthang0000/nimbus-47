# Step 4: API Upload and File Search

## Commands

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --upload-only
.\.venv\Scripts\python.exe main.py --ask "How do I add a YouTube video?"
```

These commands use `API_KEY` from the environment. Model calls are billable. The default model is `gpt-5.4-mini`; override it with `OPENAI_MODEL`. The key needs Files, Vector Stores and Responses access in the same project.

## Exact Required Prompt

You are OptiBot, the customer-support bot for OptiSigns.com. • Tone: helpful, factual, concise. • Only answer using the uploaded docs. • Max 5 bullet points; else link to the doc. • Cite up to 3 "Article URL:" lines per reply.

## Upload and Chunking

- Read the dataset from `scrape-report.json`.
- Prepare chunks of at most 3000 cl100k tokens, preferring paragraph boundaries, without overlap. Repeat title and Article URL in each chunk.
- Upload each part as a Markdown file through the Files API. `purpose=assistants` is the retrieval upload value; this does not invoke the retired Assistants API.
- Attach files through a vector-store batch with static 4096-token chunking and zero overlap. OpenAI handles embedding and indexing.
- Report source articles, prepared chunks, indexed chunk files and provider file counts separately. Internal embedding chunk totals are not directly exposed; server tokenization may differ.
- Save state atomically after each upload. Persist batch IDs to resume interrupted indexing.
- Mark files indexed only when the batch completes without failed or cancelled files.
- The store expires after seven inactive days. Renew or recreate it if needed before review.
- Unchanged uploads reuse existing files. Updated-document replacement is pending step 5.

## Artifacts

| File | Contents |
|---|---|
| `state/openai.json` | Store ID, remote file IDs and indexing state; no API key |
| `state/upload-report.json` | Source/chunk counts, provider counts, storage bytes and chunking strategy |
| `state/last-answer.json` | Response, retrieval results, citations and token usage |
| `state/last-answer.md` | Demo question and answer |

Verified: 50 source articles produced 55 indexed chunk files, zero failures and 340,908 storage bytes. An unchanged rerun reused the store/files. The YouTube query returned a grounded answer with the article URL.

## Remaining UI Evidence

Assistants API was retired on August 26, 2026. The implementation uses Responses and File Search. In the current Platform UI, save a Prompt using the exact instructions and connect File Search to the store ID from the report in the same project.

If the UI cannot support the required demo, clarify an equivalent demonstration with HR. Ask the YouTube question in the UI and capture the answer with citations. The CLI demonstration proves backend behavior but does not replace the required UI screenshot.

## References

- https://developers.openai.com/api/docs/assistants/migration
- https://developers.openai.com/api/docs/guides/tools-file-search
- https://developers.openai.com/api/reference/resources/vector_stores/subresources/file_batches/methods/create
