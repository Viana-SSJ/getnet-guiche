# Structure

```
main.py               the API: POST /chat, the conversation and operator routes, tokens, rate limit
agents/getnet/        the ADK app (works with `adk web agents`)
  agent.py            the orchestration: AGENT_TOOLS, workflow steps, make_app()
  router.py           the Router Agent: reads the message and calls the tools it needs
  knowledge.py support.py    the Knowledge and Customer Support agents, called as tools
  reply.py            the only agent that writes to the merchant
  tagger.py           the tag (a decision model) and TagPlugin
  decisions.py        the client of the OpenRouter Decisions API
  guardrails.py       the prompt rules, the masks and the answer check
  grounding.py        the number check of an answer
  chat.py             one message of a session in, one ChatResponse out; checks, fallback, history
  common.py           the model and the prompt helper
  evidence.py         the tool calls of a message: record, limit, read
  tools/              plain functions that ADK turns into tools
ingest/               build step: crawl the Getnet site into kb/ (crawl.py, convert.py)
data/                 mock merchants and their token hashes
kb/                   knowledge base snapshot (Markdown)
evals/                evaluation sets, runners, the faithfulness judge, comparisons, our labels, every result
docs/                 experiments.md: each test of the design, the model and the checks, with its numbers
observability/        Grafana dashboard and alerts
specs/                steering files and one folder per feature: requirements, design, tasks
tests/                offline tests
.github/workflows/    CI
```

Rules:

- A new agent tool is one file in `agents/getnet/` and one line in `AGENT_TOOLS`.
- A new tool is one function in `agents/getnet/tools/` and one item in an agent's `tools=[...]`.
- A behaviour change starts in `specs/`: change the requirement, then the design, then add a task.
- Each requirement names the tests or evals that prove it.
- Tests check structured fields, not the wording of a model.
