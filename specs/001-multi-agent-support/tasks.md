# Tasks: multi-agent support

Each task names the requirements it serves.

- [x] T1 Write the spec: requirements, design and tasks (all).
- [x] T2 Set up the project with uv and exact library versions (R10).
- [x] T3 Crawl the Getnet site into the Markdown knowledge base `kb/` (R12).
- [x] T4 Tools: hybrid knowledge-base search, account tools over mock data, weather, exchange rates, web search, a ticket queue in the database, with webhooks; the masks of sensitive data (R2, R3, R4, R5, R6).
- [x] T5 Agents in one ADK workflow: guard with the conversation so far, router, knowledge, support, brief, reply, the evidence of each message with a tool call limit for each agent, and the tag plugin with one decision call for the tag and P(injection) (R1, R6, R7, R8, R9, R13).
- [ ] T6 The API: `POST /chat` with sessions, tickets and the rate limit in one database, merchant tokens, the injection stop, the answer check with the number check, one replan, the fallback, the span and metrics; the conversation and operator routes; the tests (R2, R5, R7, R10, R11, R13, R14).
- [ ] T7 Docker, Docker Compose with Postgres and a data volume, the Grafana dashboard and alerts (R10, R11).
- [ ] T8 Evaluation sets and runners: dev (with follow-ups, injections and questions the knowledge base cannot answer), final, retrieval, the site's FAQ as a retrieval holdout, and public attacks with normal messages for the injection limit (R1, R2, R6, R9, R13).
- [ ] T9 Faithfulness check of saved answers (the number check, the decision model, our labels) and the comparison tools: models and variants of the design, with Wilson intervals and the exact McNemar test (R15, R16).
- [ ] T10 CI: lint and offline tests on every push, the Docker image and its `/health`, the dev set when the agents change (R10).
- [ ] T11 Run the retrieval, dev, final, faithfulness and injection evaluations, the dev set with three models and with variants of the design; keep the results in `evals/results/` (R1, R2, R8, R9, R13, R15, R16).
- [ ] T12 README: install, run, ports, agents, memory, security, RAG pipeline, testing strategy, results; `docs/experiments.md` with each test (R10, R16).
