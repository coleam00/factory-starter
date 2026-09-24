# Factory Starter

A tiny web app built to be grown by an [AI software factory](https://github.com/coleam00/ai-software-factory).
Python standard library + SQLite, nothing to install.

```bash
python -m app.server --port 8080     # then open http://127.0.0.1:8080
python -m unittest discover -s tests
```

Set `APP_NAME` to name your app. Features live in `app/features/`, one module each.
`AGENTS.md` has the conventions every agent (and person) follows.
