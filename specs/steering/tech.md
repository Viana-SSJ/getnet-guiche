# Tech

- Python 3.12.15, managed with uv only (`uv add`, `uv run`). Every library has an exact version.
- Google ADK 2.13 for agents, tools, the workflow, plugins, the server and the dev UI.
- Models through ADK `LiteLlm` on OpenRouter: DeepSeek V4 Flash, with gpt-oss-120b as the fallback.
- Knowledge-base search: `bm25s` (Portuguese stemmer), FastEmbed embeddings (local, CPU) and NumPy,
  joined by reciprocal rank fusion.
- The ADK FastAPI app with our routes only, started by `main.py` (`make agents`) or Docker Compose
  (`make docker`). Sessions (ADK `DatabaseSessionService`), tickets and the rate limit in one
  database through SQLAlchemy: a SQLite file by default, Postgres in Docker Compose.
- Free public APIs for the tools: Open-Meteo, Banco Central PTAX, Frankfurter (ECB rates), DuckDuckGo
  search.
- OpenTelemetry to `grafana/otel-lgtm` (Tempo, Prometheus, Loki, Grafana).
- Tests with pytest: they never call a real model or the network. Evaluations against the real
  model live in `evals/`. GitHub Actions runs the tests.
- A decision model (`microsoft/microsoft-decision-1`, the OpenRouter Decisions API) gives the tag and
  the faithfulness triage: typed answers with a probability, for about US$ 0.000005 a call.
- Code, comments and docs in British English, Simplified Technical English. Comments only for a
  non-obvious why. Conventional Commits, one change per commit.
- Security: a token per merchant, tools read the merchant from the session, card numbers, CPF,
  CNPJ and passwords are masked before any model and the disk, a rate limit per merchant, outbound
  HTTP goes to fixed hosts, `.env` is never committed.
