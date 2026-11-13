# Design: multi-agent support

## Flow

One ADK `Workflow`, built by `make_app()` in `agents/getnet/agent.py`:

```
START ─► guard ─► router ─► brief ─► reply ─► the merchant
                    │
                    ├─ knowledge (agent) ─► search_kb, web_search, get_weather, get_exchange_rate
                    ├─ support (agent)   ─► get_receivables, get_terminal_status, get_recent_transactions,
                    │                       knowledge (agent)
                    └─ create_ticket
TagPlugin: one decision call, in parallel, gives the tag ("Tag: …" in the reply) and P(injection).
POST /chat: masks sensitive data, loads the session, stops a likely injection, checks the answer
and, if the check stops it, runs the flow once more with the reason; saves the history; on any
failure, a ticket, an empty answer and fallback: true. A new or answered ticket goes to a webhook.
```

1. `guard` masks sensitive data (again, for the ADK dev UI), saves the masked message in the state
   (`message`, `masked`), starts a new turn (`state["turn"]`: the tool calls of this message are
   recorded under it), and puts the last 10 messages of `state["history"]` before the message. On
   a replan, it also gives the reason why the check stopped the last answer (`state["stopped"]`).
2. `router` calls the tools that the message needs (at most 6 calls) and writes an internal answer,
   in the language of the message.
3. `brief` gives the reply agent the message and the internal answer as one input.
4. `reply` writes the answer to the merchant.

## Components

| Component | File | Responsibility |
|---|---|---|
| API | `main.py` | `POST /chat`, `GET /chat/{session_id}`, the operator routes; merchant and operator tokens; rate limit. Built on `get_fast_api_app` (OpenTelemetry for every request), with the ADK routes removed |
| Database | `agents/getnet/store.py` | One SQLAlchemy engine (`DATABASE_URL`: SQLite by default, Postgres in Compose) for the ADK sessions, the tickets and the rate limit |
| Webhooks | `agents/getnet/notify.py` | `ticket.opened` and `ticket.answered`, signed with HMAC |
| Flow | `agents/getnet/agent.py` | `AGENT_TOOLS`, the `guard` and `brief` steps, `make_app()` |
| Router Agent | `agents/getnet/router.py` | `make_router()`: the prompt lists the agent tools; tools: each agent tool, `create_ticket` |
| Knowledge Agent | `agents/getnet/knowledge.py` | RAG and web search |
| Customer Support Agent | `agents/getnet/support.py` | The account tools and the knowledge agent |
| Reply agent | `agents/getnet/reply.py` | The only agent that writes to the merchant |
| Tag and injection | `agents/getnet/tagger.py` | `classify` (one decision call: the tag and P(injection)) and `TagPlugin` |
| Decision model | `agents/getnet/decisions.py` | The OpenRouter Decisions API client, for the tag and the judge |
| Chat | `agents/getnet/chat.py` | Runs the app for one message of a session, builds `ChatResponse`, stops a likely injection, checks, plans again, falls back, saves the history, records the span and metrics; `conversation()` and `answer_ticket()` |
| Shared | `agents/getnet/common.py` | `llm()` and `instruction()` |
| Evidence | `agents/getnet/evidence.py` | `CALLBACKS` of every agent (`no_tools_after_limit`, `limit_calls`, `record_tool`), `read` (the tool calls of the message), `sources_of`, `tool_calls` (each call's kind) |
| Guardrails | `agents/getnet/guardrails.py` | Prompt rules, the mask of card numbers, CPF, CNPJ and passwords, answer check |
| Number check | `agents/getnet/grounding.py` | The numbers of an answer that no source gave |
| Tools | `agents/getnet/tools/` | `kb_search.py`, `customer.py`, `web.py`, `handoff.py` |
| Ingestion | `ingest/crawl.py`, `ingest/convert.py` | Crawl the site, convert to Markdown, write `kb/` |
| Evaluation | `evals/run.py`, `evals/judge.py`, `evals/retrieval.py`, `evals/faq_holdout.py`, `evals/compare.py`, `evals/ablations.py`, `evals/injection.py` | Run the sets, check faithfulness, check retrieval, make the FAQ holdout, compare runs, build variants of the design, calibrate and test the injection limit |

## Agents

| Agent | Model input | Tools | Output |
|---|---|---|---|
| `router` | The conversation so far and the masked message | `knowledge`, `support` (ADK `AgentTool`), `create_ticket` | The internal answer |
| `knowledge` | The router's request | `search_kb`, `web_search`, `get_weather`, `get_exchange_rate` | Facts, numbers, steps and the titles of the sources |
| `support` | The router's request | `get_receivables`, `get_terminal_status`, `get_recent_transactions`, `knowledge` | Facts about the merchant's account |
| `reply` | The message and the internal answer (from `brief`) | none | The answer to the merchant |

Every agent except `reply` gets the shared prompt rules (`guardrails.PROMPT_RULES`) and today's date
(`common.instruction`). Agent tools are wrapped with `include_plugins=False`, so the tag plugin runs
once per message, not once per agent. The tag is not an agent: a decision model gives it (see Tag).

## Data flow inside agent tools

The events of an agent tool stay inside it; its changes to the session state reach the session. So:

- `router`, `knowledge` and `support` have `after_tool_callback=record_tool`. After each tool call
  it appends `{"tool": "<agent>.<tool>", "agent": <is it an agent tool>, "args", "result"}` to
  the state, under a key of its own (`evidence.<turn>.<time>.<id>`): agent tools can run at once,
  and each merges its state into the session, so a shared list would lose calls. `evidence.read`
  returns the calls of the turn that `guard` started, in order. This is the record of the message.
- Every tool reads the merchant from `ToolContext.user_id`, which ADK sets from the session, also
  inside an agent tool.

`chat.py` takes the final text of the agent that `TagPlugin` tags (the reply agent) from the events of the run, then reads the session
state: from `evidence`, the agent tools give `agents_used` and the other calls `tools_used`, the
results give `sources` (`results[].title/url`, or `source`) and `ticket` (the result of
`create_ticket`; else an open ticket of this merchant and conversation that the reply gives,
`handoff.open_ticket_in`); `tag`, `tag_confidence`, `injection` and `masked` are in the state too.

## Answer check and fallback

`guardrails.check_reply(answer, evidence, known)` returns a reason when:

- the answer is empty; or
- `knowledge` or `support` was called and `evidence` has no call of that agent; or
- a number of the answer has no source (`grounding.ungrounded`): not in `evidence`, nor in `known`
  (the router's prompt, the message and the history), nor a nearby date or a total of account
  amounts or of the amounts in reais of the conversation.

Before the check, `chat.py` stops an answer whose message has P(injection) above `INJECTION_LIMIT`
(0.3208; `evals/injection.py`): no replan, the fallback below.

On a reason, `chat.py` writes it to `state["stopped"]` and runs the flow once more (`REPLANS = 1`,
`replanned: true`): `guard` gives the router the reason, so it gets the facts again with the tools.
On a second reason, or on any exception (an ADK error event, a model or tool failure, the call limit),
`chat.py` opens a ticket in code (`open_ticket`, with the session, the masked message and, if the
check stopped an answer, that answer as a draft that was not sent) and returns an empty answer,
`handoff: true`, `fallback: true` and the ticket. It never returns HTTP 500.

## Memory

- `chat.py` uses an ADK `Runner` with `DatabaseSessionService` on the engine of `store.py`
  (`DATABASE_URL`, default `sqlite+aiosqlite:///var/getnet.db`; Docker Compose sets
  `postgresql+asyncpg://…@db:5432/getnet`). SQLite connections are not pooled, so no connection
  crosses event loops.
- Without a `session_id`, it creates a session; with one, it loads it for the token's merchant only.
  A session of another merchant is not found (HTTP 404).
- After an answer, it appends `{"role": "merchant" | "assistant", "text"}` to `state["history"]` with
  an event of its own, and keeps the last 40 items (`KEEP_MESSAGES`): each event stores the whole
  list, so with no cut the stored history grows as the square of the conversation. An operator
  answer appends `{"role": "operator", "text"}` the same way.
- `guard` gives the router the last 10 history items, then the new message. We tested that ADK
  workflow nodes do not see earlier turns by themselves: each node gets only its input.
- The message is masked before the session stores it, so no card number, CPF, CNPJ or password is
  on disk.

## Identity, limits and the operator API

- A merchant token (`Authorization: Bearer`) maps to one `user_id` through the token's SHA-256 in
  `data/customers.json`, compared with `hmac.compare_digest`. The body's `user_id` must match.
- `rate_limit` (`store.allow`): a sliding window of 60 s per merchant in the table `rate_events`, in
  one transaction: delete the old rows, count, insert. Every replica sees the same count; two
  requests at the same moment on two replicas can each pass at the limit.
- The operator token is `OPERATOR_TOKEN`; without it, the operator API is off.
- Tickets (`tools/handoff.py`) are a table in the same database: `HD-<id>`, `user_id`,
  `session_id`, `reason`, `summary`, `status` (`open`, `answered`), `answer`, `opened_at`,
  `answered_at`. `create_ticket` keeps the number of the turn in `state["ticket.<turn>"]`, so a second
  call of the same message gets the same ticket.
- `open_ticket` sends `ticket.opened` to `OPERATOR_WEBHOOK_URL`; `answer_ticket` sends
  `ticket.answered` to `MERCHANT_WEBHOOK_URL` (`notify.py`): JSON with the ticket, and
  `X-Signature: sha256=<HMAC-SHA256 of the body with WEBHOOK_SECRET>`, timeout 3 s. A failure is
  logged; the queue and the conversation have everything.
- Every agent has `limit_calls` as `before_tool_callback`: it counts the tool calls of each agent in
  the turn (`calls.<turn>.<agent>`) and, after 6, returns an error instead of running the tool. And
  `no_tools_after_limit` as `before_model_callback`: after 6 calls, the model gets no tools, so it
  must write its answer. In Docker the router once called `create_ticket` again and again, ignored the
  error, and stopped only at 50 model calls, after 108 s and five tickets.
  `RunConfig(max_llm_calls=50)` is a last stop. We measured that ADK's count is not simply per agent
  or per message, so the limit that we rely on is our own.

## Faithfulness check

- `evals/run.py` saves `evidence` for each answer, with the evidence of the earlier messages of a
  conversation.
- `agents/getnet/grounding.py` finds the dates, times, phone numbers and numbers of the answer, in one form
  each ("09/11/2026" and "2026-11-09" are the same date; "45,12" and "45.12" the same number). Each
  must be in the evidence (also the digits inside a name, and a date in a file name), the router's
  prompt, the message, the conversation so far, or the dates of yesterday, today and tomorrow, or be
  a total of the amounts of one `get_receivables` or `get_recent_transactions` result, or of the
  amounts in reais ("R$ 116,77") of the conversation so far: a follow-up can add them up. Counts up to
  10 and years are free. The API and the judge run the same check.
- `evals/judge.py` sends the instructions, message, evidence and answer to the OpenRouter Decisions
  API (`microsoft/microsoft-decision-1`) and gets P(faithful). It does not fail an answer; it
  flags it for a person. The threshold is split conformal: the ceil((n + 1)(1 − α))-th smallest
  P(faithful) of the n unfaithful answers of the calibration runs, with α = 0.2.

## Tag

`TagPlugin(reply_author="reply")` is an ADK plugin on the `App`:

- `before_run_callback`: starts `classify` on the masked message, as an asyncio task. `classify`
  makes one call to a decision model (`decisions.adecide`, `microsoft/microsoft-decision-1`) with two
  questions: `tag`, a `choice` with the five tags and their criteria, and `injection`, a `noul`
  (yes or no) question. It returns the tag, its probability and P(injection).
- `on_event_callback`: on the reply agent's final event, it waits for the task, adds the part
  `"\n\nTag: <tag>"` and sets `state_delta["tag"]`, `["tag_confidence"]` and `["injection"]`.
- `after_run_callback`: cancels a task that was not used.
- A failure of the decision model gives `other`, no confidence and no P(injection): the injection
  check then lets the message through, and the prompt rules and the design of the tools remain.

## Knowledge base search

- Files: `kb/**/*.md`, without the files that the `EXCLUDE` pattern in `kb_search.py` names: index
  and report files, the blog, careers, press, sponsorship and ESG pages, policies, regulations and
  other PDFs that are not about products. 104 of the 190 files are searched.
- Chunks: one per Markdown heading; sections longer than 250 words are cut into windows of 250 words
  with 25 words of overlap. Duplicate chunks are removed.
- Embeddings: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (FastEmbed, ONNX, CPU),
  of title and text, normalised. Cached in `.index/` under a hash of the files; rebuilt when `kb/`
  changes.
- BM25: `bm25s` with the Portuguese stemmer and stop words, over title and text.
- Search: the top 18 of each method, joined by reciprocal rank fusion (`1 / (60 + rank)`), top 6
  returned with title, URL and text.

## Data models

- `ChatResponse`: `answer: str`, `tag: str`, `tag_confidence: float | None`, `agents_used: list[str]`,
  `tools_used: list[str]`, `sources: list[{title, url}]`, `handoff: bool`, `ticket: str | None`,
  `masked: list[str]`, `replanned: bool`, `fallback: bool`, `session_id: str | None`, `model: str`,
  `latency_ms: int`, `request_id: str`; and, which the API does not return, `evidence: list[{tool,
  agent, args, result}]`, `draft: str` (an answer that the check stopped) and `injection: float | None`
  (an attacker must not learn how near a message came to the limit).
- KB file: front matter `title`, `source` (URL), `kind` (`page`, `faq`, `pdf`), `fetched` (date), then
  Markdown.
- Mock merchants (`data/customers.json`): plan, rates per method, terminals, transactions with
  `day_offset` (days from today, so "yesterday" always has data).
- Mock tokens: `demo-token-<user_id>` for each mock merchant.

## Model

`common.llm()`: ADK `LiteLlm` with `AGENT_MODEL` (default `openrouter/deepseek/deepseek-v4-flash-0731`),
`num_retries=2`, `timeout=60`, `temperature=0.1`, and, for OpenRouter models, `extra_body.models`
with `AGENT_FALLBACK_MODELS` (default `openai/gpt-oss-120b`).

## Observability

```
agents container ── OTLP over HTTP (4318) ──► observability container (grafana/otel-lgtm)
  ADK spans, metrics, logs                       OpenTelemetry collector ─► Tempo, Prometheus, Loki
  chat span, chat.requests, chat.latency,        Grafana (3000) with observability/dashboard.json
  chat.tool_calls                                and observability/alerts.yaml
```

ADK exports by itself when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (Docker Compose sets it). The
dashboard uses cumulative counters for totals, tags and percentiles, so they show data after the
first export, and `rate()` only for the graphs over time (messages per minute, latency p50 and p95).

`observability/alerts.yaml` provisions two Grafana alert rules, evaluated every minute: the share of
fallbacks in `increase(chat_requests_total[10m])` above 5 %, and the p95 of `chat.latency` above
30 s, each for 10 minutes. `increase()` does not count the first value of a new series, so a burst
of failures in the first export is seen from the next one.

## Decisions

| Decision | Why | Alternative |
|---|---|---|
| A router with agents as tools (ADK `AgentTool`) | One agent decides; one message can need several agents (a machine problem needs the account and the manual) | A router that sends each message to one specialist |
| Keep the agent tools, though one agent passed as many | One agent with every tool passed as many dev cases (tags aside) with half the tool calls, and 8/8 like the agent tools on 8 messages that need several sources (a hypothesis written before the run; `docs/experiments.md`). The challenge asks for three agent types, and a new agent is one file | One agent with every tool |
| An ADK `Workflow` for the flow | The steps are explicit in one place; the dev UI draws them | ADK sub-agents with `transfer_to_agent` (a transfer does not come back, so no step can run after it); `SequentialAgent` (deprecated in ADK 2) |
| A reply agent for every answer | One voice; the router and the agent tools focus on facts | The router answers the merchant |
| The reply agent gets the message (`brief`), and the internal answer is in the message's language | The knowledge base is in Portuguese, so without this the reply often followed the Portuguese internal answer | The message in the system prompt only |
| The knowledge agent searches the knowledge base first for payment questions | Payment terms such as "gravame" also have web results, which are not Getnet's answer | Let the model choose freely |
| The tag in an ADK plugin | It shows in every entry point (the dev UI and `POST /chat`) and runs in parallel | The tag in `POST /chat` only |
| A decision model for the tag, not an LLM agent | On the dev set, with no tuning: 39/40 and the same tag in two runs; the LLM tagger gave 37 to 39 over six runs. It costs about US$ 0.000005, and returns a probability | The LLM tagger (one more model call per message) |
| Mask sensitive data; failures return data, not text | The merchant gets a real answer in their language; the client app writes the failure message | A fixed safety reply and a fixed failure reply |
| The history in the session state, passed by `guard` | Workflow nodes see only their input; one list is also what `GET /chat/{session_id}` returns | ADK memory services (search over past sessions, not the current conversation) |
| One database for sessions, tickets and the rate limit, through SQLAlchemy; Postgres in Compose | API replicas share conversations, tickets and the message count; SQLite stays the default, so tests and `make agents` need no service | Redis for the rate limit (a service more, for one table); SQLite only (one process) |
| Plan again once when the check stops an answer | The check stops few answers, and each stop sent a merchant to a person. With the reason, the router can get the facts again | A ticket at once; more replans (each one adds a whole run) |
| The injection check in the tag's decision call, after the run | No call and no time more; the tools can only read the session's merchant, and the only action is a ticket, so stopping the answer is enough | A check before the router (adds the call's time to every message); a fine-tuned classifier; patterns (an attack in Portuguese has many forms) |
| Webhooks for new and answered tickets | The operator and the merchant learn at once, with no polling and no new message; one function, signed with HMAC | Telegram in the API (a token and a chat id per operator team: a relay can do it from the webhook) |
| Mask in `chat.py` before the session | The session is stored on disk | Mask only in `guard` (the raw message would be on disk) |
| Token hashes in the mock data | No secret in Git; the same check as a real token store | `user_id` from the body only |
| No ADK route in the API | They have no authentication: `/run` takes any `user_id`. The dev UI runs alone with `make web` | Leave the dev UI on port 8000 |
| The number check in the API, not only in the evaluation | A wrong amount or date is the costliest error for a merchant. The check is free; over every saved answer it caught 458 of 475 changed numbers and stopped none of 1,063 sent answers, after four fixes with tests (a date in a file name, a phone number with an en dash, a number before "/mês", the total of two amounts of the previous answer) | Only measure it offline |
| The knowledge agent makes its searches in one step, at most 3 | In a controlled ablation: 2.5 tool calls per message against 3.0, and 3 repeated or blocked calls against 8, with no change in passes or latency that the dev set can show | Search again until the results answer |
| A decision model for faithfulness triage, with a split conformal threshold | It ranks answers (AUC 0.70 on 203 labels) but cannot be a gate. A threshold picked by eye did not transfer; the conformal one has a stated guarantee and on the next day's runs flagged 9 of 13 faults with under half the answers read | An LLM judge as the gate (up to 17 false alarms in 29); a local NLI check per claim (up to 9 in 10) |
| `record_tool` writes each call to the state, under a key of its own | Agent tool events do not reach `chat.py`; the state does. One record gives the fields, the answer check, the metrics and the evidence for the judge; a key per call, because a shared list lost calls when agent tools ran at once | Reading function calls from events and state changes from several places |
| The ADK FastAPI app as the base | OpenTelemetry for every request with no extra code | Our own FastAPI app |
| Hybrid retrieval with plain `bm25s`, FastEmbed and NumPy | BM25 finds product names and rare words, embeddings find paraphrases and English; no framework needed for 1,316 chunks | Vector search only; LlamaIndex (ADK's `LlamaIndexRetrieval` returns one chunk and no source) |
| Official APIs for weather and rates, with a second source for rates | Exact numbers with a source; the PTAX API can return HTTP 502 | Web snippets |
| DeepSeek V4 Flash, with a fallback model | On the same 40 dev messages: 38/40 for US$ 0.00098 a message, against gpt-oss-120b (34/40, US$ 0.00082) and Qwen 3.7 Flash (36/40, US$ 0.00076, p95 117 s). It lost no case to either; no gap is significant with 40 messages (paired sign test), so latency and fallbacks decide too (`evals/compare.py`) | Qwen 3.7 Flash, the cheapest; free models (HTTP 429 and 50 requests a day without credits) |
| The knowledge base in Git; ingestion as a build step | The same build every time; no crawling at runtime | A crawl at build time or an ingestion API |
| One `grafana/otel-lgtm` container | Traces, metrics, logs and dashboards in one standard OpenTelemetry service | Several services, or an LLM-only tool |

## Error handling

| Failure | Behaviour |
|---|---|
| Model HTTP 429 or down | LiteLLM retries twice; OpenRouter tries the fallback model; then the fallback ticket |
| Public API down or not JSON | The tool returns `{"error": ...}`; rates try the ECB; the agent says the service is unavailable |
| Unknown merchant | The account tools return `{"error": "Merchant not found."}` |
| Decision model failure | Tag `other`, no confidence; the answer is not affected |
| Any other exception in `POST /chat` | A ticket; HTTP 200 with an empty answer and `fallback: true` |
| An agent calls tools in a loop | After 6 calls of one agent, a tool returns an error and the model gets no tools; after 50 model calls, ADK stops the run and the fallback ticket opens |
| The answer check stops an answer, or the model returns no content (`MODEL_RETURNED_NO_CONTENT`) | The flow runs once more with the reason; a second stop opens the fallback ticket |
| A likely prompt injection | No answer; the fallback ticket, with the reason |
| A webhook fails | A log line; the answer is not affected |
| No token, a wrong token, another merchant | HTTP 401, 401, 403; a session of another merchant: 404 |
| Too many messages | HTTP 429 with `Retry-After: 60` |

## Testing strategy

- **Unit** (`make test`): tools (fees, payment dates, business days, the ECB fallback, errors instead
  of exceptions, `record_tool`), the masks, ingestion filters and allowed hosts, the API contract,
  tokens, rate limit, the operator API, no ADK route in the API, pinned versions, and the number check.
- **Integration** (`make test`, `tests/test_chat.py`): the real workflow, agents, agent tools,
  runner, plugin and tools, with a fake model per agent (`fake/<agent>`). The fake router follows a
  plan of tool calls. Memory, a restart with SQLite, the operator answer, the webhooks, the replan,
  the injection stop and the call limit are tested here. Assertions are on structured fields only.
- **CI**: GitHub Actions runs Ruff and the unit and integration tests on every push, builds the
  Docker image and checks `/health` in it, and runs the dev set when the agents change and the key
  is set.
- **Injection** (`evals/injection.py`): P(injection) on 300 public attacks in Portuguese, 60 in
  English and German, our 3, and on normal messages: the 309 FAQ questions (half calibrate the
  limit), our dev and final messages and 56 normal texts.
- **Retrieval** (`make eval-retrieval`): our 27 questions with the expected page (and, for some, the
  expected passage in the same result), and a holdout that we did not write: the 309 FAQ questions
  of the site, in Portuguese and translated to English by the model (`evals/faq_holdout.py`).
  hit@1, hit@3, hit@6 and the mean reciprocal rank.
- **Model** (`make eval`, `make eval-final`): the dev set (40 messages: 3 follow-ups in a
  conversation, 3 injections, 2 questions that the knowledge base cannot answer) to tune prompts;
  the 10 challenge messages as the final set. A case passes when an expected tool is called (or no
  tool, when none is expected), every source in `expect_all` is used, the answer has the facts in
  `must_contain`, the tag is right, a `search_kb` answer has a `getnet.com.br` source, the expected
  kinds are masked, the answer is not empty and has no forbidden text (another merchant's data, a
  masked secret), and there is no fallback.
- **Faithfulness** (`make judge`): the number check and the decision model, against our labels.
- **Comparisons** (`make compare`, `evals/compare.py`, `evals/ablations.py`): models and variants on
  the same cases, with Wilson intervals and the exact McNemar test; see `docs/experiments.md`.
