.PHONY: agents web test eval eval-final eval-retrieval judge compare ingest docker observability

agents: .env ## Start the API on http://127.0.0.1:8000
	uv run python main.py

web: .env ## The ADK dev UI (adk web) on http://127.0.0.1:8001/dev-ui, to try and trace the agents (local only)
	uv run adk web --port 8001 agents

test: ## Offline tests: no network, no LLM, about 2 seconds
	uv run pytest -q

eval: .env ## Dev evaluation set against the real model (about 6 minutes, under US$ 0.05)
	uv run python -m evals.run evals/dev.jsonl

eval-final: .env ## The 10 challenge messages
	uv run python -m evals.run evals/final.jsonl

judge: .env ## Check the faithfulness of the last dev results with the judge model
	uv run python -m evals.judge $$(ls -t evals/results/dev-*.json | head -1)

compare: ## The dev runs of three models, with docs/cost-quality.svg (other runs: see docs/experiments.md)
	uv run python -m evals.compare models

eval-retrieval: ## Retrieval quality of search_kb (offline): our questions, and the site's FAQ in Portuguese and English
	uv run python -m evals.retrieval evals/retrieval_dev.jsonl evals/retrieval_faq_pt.jsonl evals/retrieval_faq_en.jsonl

ingest: ## Crawl the Getnet site again and rewrite kb/ (about 4 minutes)
	uv run python -m ingest

docker: .env ## Build and start the API and Grafana (http://localhost:3000) in Docker
	docker compose up --build

observability: ## Only Grafana and the OTLP endpoint in Docker, for `make agents` with OTEL_EXPORTER_OTLP_ENDPOINT
	docker compose up observability

.env:
	@cp .env.example .env
	@echo "Created .env from .env.example. Put your OPENROUTER_API_KEY in it, then run the command again." && exit 1
