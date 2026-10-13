# Step 2: Python and Configuration

On this Windows machine, Python is available through the `py` launcher. The global `python` command points to the Microsoft Store shortcut. Use the virtual-environment executable directly; activation and ExecutionPolicy changes are unnecessary.

```powershell
cd C:\workspace\prepare-interview\projects\nimbus-47
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.sample .env }
```

Edit `.env` locally:

- `AI_PROVIDER=openai`: the implemented provider. Gemini is a recognized configuration value, but its backend is not implemented.
- `API_KEY`: your provider key. Never include it in Git, chat or videos.
- `ARTICLE_LIMIT=50`: the target dataset size; the brief requires at least 30.
- Keep other defaults initially. Shell environment variables override `.env` values.

```powershell
.\.venv\Scripts\python.exe main.py --check-config
git status --short
```

Expected result: `Configuration valid` and exit code zero, without displaying the key. This is local validation; it does not call the provider or verify credential validity. Invalid configuration exits with code one.

`main.py` dispatches the available actions. Configuration is handled by `src/config.py`. The virtual environment, `.env`, generated data and runtime state are excluded from Git. See subsequent step guides for ingestion and API operations.
