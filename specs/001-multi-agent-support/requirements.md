# Requirements: multi-agent support

Each requirement has acceptance criteria (GIVEN / WHEN / THEN) and its proof: an offline test in
`tests/`, or a check of `evals/` against the real model. A change of behaviour starts here.

## R1 The router and its agent tools

As a merchant, I want my message answered with every piece of information it needs.

- GIVEN a message, THEN the `router` agent chooses the tools to call. It can call several, and the
  same one more than once: the `knowledge` agent, the `support` agent and `create_ticket`.
- GIVEN a message about the merchant's own machine, sales, money or account, THEN the router calls
  `support`.
- GIVEN a greeting, thanks, a question about the service, or an off-topic or harmful request, THEN
  the router calls no tool.
- GIVEN a new agent added to `AGENT_TOOLS`, THEN the router can call it, with no other change: the
  router's prompt lists the name and description of every agent tool.
- GIVEN a message, THEN each agent (router, knowledge, support) makes at most 6 tool calls; a later
  call returns an error and does not run. ADK stops a run after 50 model calls (`max_llm_calls`), a
  last stop.
- GIVEN the dev set, THEN the expected tools are called in 90 % or more of the cases. GIVEN the 10
  messages of the challenge, THEN in 10 of 10.

The three agent types of the challenge: Router Agent = `router`; Knowledge Agent = `knowledge` (RAG
and web search); Customer Support Agent = `support` (three account tools and the knowledge agent).

Proof: `test_each_request_calls_its_tools`, `test_a_new_agent_tool_needs_one_line`,
`test_the_router_stops_after_its_call_limit`, `test_the_model_call_limit_is_a_fallback`, `evals/run.py`.

## R2 Grounded answers

As a merchant, I want answers that I can trust.

- GIVEN a question about Getnet or payments, THEN the knowledge agent calls `search_kb` first, and the
  answer has at least one source with a `getnet.com.br` URL.
- GIVEN the `knowledge` or `support` agent is called and calls none of its own tools, THEN the
  answer is not sent (see R7).
- GIVEN an answer, THEN every number, amount, date, time and phone number in it is in the tool calls
  and results (also the digits inside a name, and a date in a file name), the router's prompt, the
  message, the conversation so far or the dates of yesterday, today and tomorrow, or is a total of
  the amounts of one account tool result or of the amounts in reais that the conversation gave. Counts up to 10 and years are free. Else the answer is not
  sent (see R7), and a person gets it as a ticket.
- GIVEN a question that the knowledge base cannot answer, THEN the answer says so and invents no
  number (the dev cases marked `absent`; we read the answers).
- GIVEN the 309 FAQ questions of the site (`evals/retrieval_faq_pt.jsonl`, a holdout we did not
  write), THEN `search_kb` has the page of the question in its top 6 for 95 % or more.

Proof: `test_a_number_that_no_tool_gave_goes_to_a_person`, `test_a_number_of_an_earlier_message_can_come_back`,
`test_knowledge_returns_its_sources`, `test_record_tool_writes_each_call_and_the_sources_come_from_the_results`,
`test_an_agent_tool_without_its_own_tools_is_a_fallback`,
`evals/run.py` (source check, `search_kb` for product questions, `absent_passed`), `evals/retrieval.py`
(our questions and the FAQ holdout), `evals/judge.py`.

## R3 General questions

As a merchant, I want quick answers about the weather, exchange rates and general facts.

- GIVEN a weather question, THEN the knowledge agent calls `get_weather` (Open-Meteo, today to 7
  days ahead).
- GIVEN an exchange-rate question, THEN the knowledge agent calls `get_exchange_rate` (Banco Central
  PTAX of the last 7 days; the European Central Bank rate when PTAX does not answer).
- GIVEN another general question, THEN the knowledge agent calls `web_search` (DuckDuckGo, 5 results).
- GIVEN a public API fails, THEN the tool returns `{"error": ...}` and does not raise.

Proof: `test_tools_refuse_bad_input_without_a_network_call`,
`test_exchange_rate_falls_back_to_the_ecb_when_ptax_is_down`,
`test_tools_return_an_error_instead_of_raising_when_apis_are_down`.

## R4 Account support

As a merchant, I want answers about my own payments, sales and machines.

- GIVEN a session of a merchant, WHEN any tool runs (also inside an agent tool), THEN it reads that
  merchant's data only. No tool takes a user id from the model.
- GIVEN an unknown `user_id`, THEN the account tools return an error.
- GIVEN a question about when money arrives, THEN `get_receivables` gives, for each approved sale of
  the day, the gross amount, the fee, the net amount and the payment date (debit: 1 business day,
  credit: 2 business days, Pix: the same day).
- GIVEN a declined sale, THEN `get_recent_transactions` gives its decline code and reason.
- GIVEN a machine problem, THEN `support` calls `get_terminal_status` and asks `knowledge` for the
  steps for that machine model.

Proof: `test_tools_use_the_session_user_not_the_model`, `test_receivables_use_the_user_from_the_context_only`,
`test_unknown_user_gets_no_data`, `test_receivables_exclude_declined_sales_and_compute_fees`,
`test_business_days_skip_weekends`.

## R5 Human handoff (bonus)

As a merchant, I want to reach a person when the chat cannot help, and get the person's answer in
the same chat.

- GIVEN I ask for a person, complain, am unhappy, want or threaten to cancel, or need an action that
  only a person can take, THEN the router calls `create_ticket`, and the reply gives the ticket
  number and the channels. The ticket promises no deadline. GIVEN the conversation already has a
  ticket for the same request, THEN the reply gives that number again and opens no new ticket, and
  `ticket` has it: a ticket number in the reply counts only if it is an open ticket of this merchant
  and this conversation.
- One message opens at most one ticket: a second `create_ticket` call of the same message gets
  the same number.
- The ticket stores the `user_id` and the `session_id` of the session, in the database (R13): it
  survives a restart.
- GIVEN a ticket opens and `OPERATOR_WEBHOOK_URL` is set, THEN the API sends `ticket.opened` to it
  at once. GIVEN an operator answers and `MERCHANT_WEBHOOK_URL` is set, THEN the API sends
  `ticket.answered`, with the `session_id` and the answer, to the back end of the merchant app, which
  can send a push notification: the merchant sees the answer with no new message. Each request
  has `X-Signature: sha256=<HMAC-SHA256 of the body with WEBHOOK_SECRET>`. GIVEN a webhook fails,
  THEN only a log line says so: the queue and the conversation have everything.
- GIVEN the operator token, THEN `GET /tickets?status=open` lists the queue, and
  `POST /tickets/{number}/answer` answers an open ticket once. The answer goes into the merchant's
  conversation: `GET /chat/{session_id}` shows it, and the router reads it with the next message.
- GIVEN no operator token, or a wrong one, THEN the operator API answers HTTP 401; GIVEN no
  `OPERATOR_TOKEN` setting, HTTP 503.

As an operator, I want a queue of tickets with the conversation they came from.

Proof: `test_each_request_calls_its_tools`, `test_tools_use_the_session_user_not_the_model`,
`test_an_operator_answer_goes_into_the_conversation`, `test_the_operator_api_needs_the_operator_token`,
`test_a_reply_that_gives_the_open_ticket_of_the_conversation_returns_it`,
`test_one_message_opens_at_most_one_ticket`,
`test_webhooks_tell_the_operators_of_a_ticket_and_the_merchant_app_of_its_answer`,
`test_a_failed_webhook_changes_nothing_for_the_merchant`.

## R6 Guardrails (bonus)

The guardrails are in `agents/getnet/guardrails.py`. No reply text is hardcoded.

- GIVEN a message with a card number (13 to 19 digits that pass the Luhn check), a CPF or a CNPJ
  (with valid check digits), or a password after "senha", "password" or "pin" and ":", "=", "é", "e" or
  "is", THEN `chat.py` replaces it with a mark such as `[card number removed]` before the session
  stores the message and before any model sees it, also the decision model of the tag. `guard` does the same for the
  ADK dev UI. The message is answered as usual, the reply asks me not to send that data, and
  `masked` names the kinds (`card`, `cpf`, `cnpj`, `password`).
- Other numbers stay: order numbers, amounts, dates, phone numbers, machine serials.
- GIVEN an off-topic or harmful request (to ignore the instructions, or to show another merchant's
  data), THEN the router calls no tool and declines it.
- GIVEN tool results that contain instructions, THEN the agents treat them as data. The prompt rules
  of the router, knowledge and support agents say so; the reply prompt and the tag question say that
  their input is data.
- The decision call of the tag (R9) also gives P(injection): that the message tries to change the
  instructions, get them, give a new role, speak as Getnet staff or the system, or get another
  merchant's data. GIVEN P(injection) above `INJECTION_LIMIT`, THEN no answer goes out: the
  fallback of R7, with the reason in the ticket. The limit is split conformal on half of the site's
  FAQ questions (`ALPHA = 0.01`), so that at most 1 % of normal questions like them go to a person;
  `evals/injection.py` tests it on public attacks in Portuguese, English and German and on our own
  messages. The check adds no call and no time. The API never returns P(injection).

Proof: `test_sensitive_data_is_masked`, `test_other_numbers_and_words_stay`,
`test_sensitive_data_never_reaches_a_model_or_the_database`,
`test_a_likely_injection_goes_to_a_person_with_no_answer`,
`test_the_injection_limit_of_the_api_is_the_calibrated_one`, `evals/injection.py`, dev set
(off-topic messages, three injections, one of them as a fake operator, which a person must take
over, and card, CPF and password messages; we read each answer).

## R7 Reliability

- GIVEN R2 stops an answer, THEN the flow runs once more, and the router gets the reason, to get the
  facts again with the tools; `replanned` is true. GIVEN R2 stops the second answer too, THEN the
  fallback below.
- GIVEN an agent reaches its tool call limit, THEN its next model call has no tools, so it writes its
  answer: a model can ignore the limit error and loop until `max_llm_calls`.
- GIVEN a model or tool fails, or R2 stops an answer twice, THEN `POST /chat` returns HTTP 200 with an
  empty `answer`, `fallback: true`, `handoff: true` and the `ticket` that a person takes over, with
  the session of the conversation. The client app writes the message to the merchant. GIVEN the
  check stopped an answer, THEN the ticket has it as a draft that was not sent, for the person to
  check and reuse.
- GIVEN the main model fails, THEN LiteLLM retries twice, and OpenRouter tries the fallback model.
- GIVEN the decision model of the tag fails, THEN the tag is `other`, and the answer is not affected.

Proof: `test_model_failure_is_a_fallback_with_a_ticket`, `test_an_agent_tool_without_its_own_tools_is_a_fallback`,
`test_a_number_that_no_tool_gave_goes_to_a_person` (the draft in the ticket), `test_tagger_failure_gives_other`,
`test_a_stopped_answer_is_planned_again_once_with_the_reason`, `test_the_router_stops_after_its_call_limit`,
`test_calls_at_once_past_the_limit_get_an_error`, `evals/ablations.py wrong-number` (the replan with a
fault that we inject).

## R8 One agent writes to the merchant

As a merchant, I want every reply in one clear voice and in my language.

- GIVEN any message, THEN the router writes an internal answer from what its tools returned, and the
  `reply` agent writes the reply from it. The reply agent keeps every fact, number, date, step,
  ticket number and source, and adds none.
- GIVEN a message in a language, THEN the internal answer and the reply are in that language, also
  when the message has Portuguese terms in an English sentence ("antecipação", "Get Clássica").
- The reply agent gets the message as its input, not only the internal answer, because the
  knowledge base, and so the internal answer, is often in Portuguese.

Proof: `test_each_request_calls_its_tools` (the answer is the reply agent's), final set (read each
answer).

## R9 Conversation tag

As an operations team, we want every message tagged, so that we can count and route the work.

- GIVEN a message, THEN it gets exactly one tag:
  - `banking`: money and the account (Get Conta, Pix, receivables, payment dates, sales advance,
    loans, rates);
  - `backoffice`: operations (card machine, connection, registration, settings, a sale declined by
    an error);
  - `chargebacks`: disputes, refunds, wrong charges, fraud;
  - `churn`: cancelling, dissatisfaction, a threat to leave Getnet;
  - `other`: anything else.
- GIVEN the reply, THEN it ends with "Tag: <tag>" in the ADK dev UI (`make web`), and the session
  state has `tag`. `POST /chat` returns it in `tag`, with no tag line in `answer`.
- A decision model gives the tag and its probability (`tag_confidence`), from the masked message;
  it starts when the message arrives and runs in parallel with the agents.
- GIVEN the dev set, THEN 90 % or more of the tags are right. GIVEN the final set, which has the
  expected tags since 2026-11-09 (written before any tagger ran on them), THEN 9 of 10 or more.

Proof: `test_the_tag_ends_the_reply_and_fills_the_field`, `test_tagger_failure_gives_other`,
`evals/run.py` (dev and final tags).

## R10 API and operations

- GIVEN `POST /chat` with `{"message": 1 to 2,000 characters, "user_id": [A-Za-z0-9_.-], 1 to 64,
  "session_id": optional, [A-Za-z0-9-], up to 64}` and a valid merchant token, THEN the reply has
  `answer`, `tag`, `tag_confidence`, `agents_used`, `tools_used`, `sources`, `handoff`, `ticket`,
  `masked`, `replanned`, `fallback`, `session_id`, `model`, `latency_ms` and `request_id`. Invalid input gets HTTP
  422.
- The API serves `POST /chat`, `GET /chat/{session_id}`, the operator routes, `/health` and `/docs`,
  and no ADK route: `/run`, `/run_sse` and the session routes have no authentication. `make web`
  starts the ADK dev UI on port 8001 for local work.
- GIVEN a machine with uv, THEN `make agents` starts the service. GIVEN Docker, THEN `make docker`
  starts it with Postgres and Grafana, and a volume keeps sessions and tickets.
- Every library has an exact version (`==`) in `pyproject.toml`; `uv.lock` pins the rest.
- One JSON log line per message, without the message text.
- GIVEN a push, THEN GitHub Actions runs the linter (Ruff) and the offline tests, and builds the
  Docker image and checks that the API in it answers `/health`. GIVEN a push that changes `agents/`,
  `evals/` or the libraries, and an `OPENROUTER_API_KEY` secret, THEN it also runs the dev set and
  fails below 90 % passed.

Proof: `test_chat_endpoint_returns_the_reply_contract`, `test_chat_endpoint_validates_input`,
`test_the_adk_routes_without_authentication_are_off`, `test_dependencies_are_pinned`, `make docker`,
`.github/workflows/ci.yml`.

## R11 Observability

As an operator, I want to see what the service does when it runs in Docker.

- GIVEN `make docker`, THEN a second container (`grafana/otel-lgtm`) receives the OpenTelemetry
  traces, metrics and logs, and Grafana opens the "Getnet agents" dashboard on port 3000.
- Every `POST /chat` message is one trace: a `chat` span (agents, tools, tag, tag_confidence,
  handoff, masked, fallback, the number of sources and of tool calls, request_id) with the ADK spans
  of the workflow, agents, model calls and tools inside it.
- Three metrics of our own: `chat.requests` (by agents, tag and fallback), `chat.latency`, and
  `chat.tool_calls` (by calling agent and kind: `run`, `repeat` of the same tool with the same
  arguments, `blocked` by the limit). The dashboard shows the tool calls per message by agent and
  kind, and the share of repeated or blocked calls; the evaluation reports both per run.
- GIVEN no `OTEL_EXPORTER_OTLP_ENDPOINT`, THEN nothing is exported.
- No message text and no secret goes into traces, metrics or logs.
- Grafana has two alert rules: fallbacks above 5 % of messages, and a p95 latency above 30 s, each
  for 10 minutes.

Proof: `test_chat_records_a_span_and_metrics` (also: no span holds the message text),
`test_tool_calls_are_counted_by_agent_and_kind`, `make docker`
(every dashboard query returns data; with a broken model, the fallback rule goes to pending).

## R12 Knowledge base

- GIVEN `make ingest`, THEN the crawler reads `site.getnet.com.br` (pages and PDFs, not the blog) and
  writes Markdown files with front matter to `kb/`, without the site menu, header, footer, hidden
  elements and repeated lines. A line that is on 30 % or more of the web pages (and on 3 or more) is
  removed, except a heading; PDFs keep all their lines. FAQ pop-ups become `## question` and answer.
- GIVEN a URL outside the Getnet hosts or not HTTPS, THEN the crawler refuses it, also after a
  redirect.
- The knowledge base is a build step, not an API: `kb/` is in Git.

Proof: `test_faq_becomes_heading_and_answer_without_menu`,
`test_boilerplate_removes_shared_lines_but_keeps_headings_and_content`,
`test_boilerplate_ignores_pdfs_when_counting`, `test_crawler_refuses_hosts_outside_the_allow_list`.

## R13 Memory

As a merchant, I want to continue a conversation: "and how do I restart it?" after a question about
my machine.

- GIVEN a reply, THEN it has a `session_id`. GIVEN the next message with that `session_id`, THEN the
  router gets the last 10 messages of the conversation (merchant, assistant and operator), marked as
  data, before the new message.
- GIVEN no `session_id`, THEN a new conversation starts.
- Sessions are in a database (`DATABASE_URL`): a SQLite file by default, Postgres in Docker
  Compose, so a conversation survives a restart and several API replicas share it. The ADK session
  service, the tickets and the rate limit use one engine.
- A session keeps the last 40 messages: each change of the history stores the whole list.
- GIVEN a message, THEN `agents_used`, `tools_used` and `sources` are of that message only.
- GIVEN the dev set, THEN its three follow-up messages pass: "E como eu reinicio ela?" names the Get
  Smart, "E o do débito, cai quando?" has the amount of the debit sale, and "Quero falar com uma
  pessoa sobre essa cobrança" opens no new ticket for a request that has one.

Proof: `test_the_next_message_knows_the_conversation`,
`test_a_new_message_without_session_id_starts_a_new_conversation`,
`test_the_conversation_survives_a_restart`, `test_each_message_reports_only_its_own_tools`,
`test_a_session_keeps_only_the_last_messages`,
`evals/run.py` (cases with `before`).

## R14 Identity and limits

As Getnet, we want each merchant to reach only their own data.

- GIVEN `POST /chat` or `GET /chat/{session_id}` without a valid merchant token
  (`Authorization: Bearer`), THEN HTTP 401. The token's SHA-256 is in `data/customers.json`; in
  production, the Getnet app's login issues the token.
- GIVEN a token and a `user_id` of another merchant, THEN HTTP 403.
- GIVEN a `session_id` of another merchant, THEN HTTP 404, as for an unknown session.
- GIVEN more than `RATE_LIMIT_PER_MINUTE` messages (default 20) from one merchant in one minute, THEN
  HTTP 429. The count is in the database, so every API replica shares it; two replicas can each
  let one more message through at the same moment.

Proof: `test_chat_needs_the_token_of_the_same_merchant`,
`test_a_merchant_cannot_use_the_conversation_of_another`, `test_chat_endpoint_validates_input`,
`test_each_merchant_has_a_rate_limit`, `test_the_rate_limit_is_shared_by_every_api_replica`.

## R15 Faithfulness check

As a team, we want to know that answers say only what the tools returned.

- `evals/run.py` keeps the tool calls and results of each answer (`evidence`).
- `agents/getnet/grounding.py` finds a number that R2 does not allow. It is free and deterministic;
  the API runs it on every answer, and the judge on saved answers.
- `evals/judge.py` also asks a decision model (`microsoft/microsoft-decision-1`, no web search) for
  the probability that the answer is faithful. A person reads the answers at or below a threshold.
  Split conformal prediction sets the threshold from the unfaithful answers of the calibration runs,
  so that the triage flags at least 80 % of unfaithful answers like them (`ALPHA = 0.2`).
- `evals/labels.jsonl` has our labels: faithful or not, with the reason, for 203 answers of eight
  runs; a label counts only for its run. The runs of 2026-11-09 calibrate; the runs of 2026-11-10
  test (`uv run python -m evals.judge calibrate`). With `--corrupt`, each faithful final answer also
  gets a copy with one number changed, which must fail.

Proof: `test_numbers_from_the_tools_are_grounded_in_any_format`,
`test_a_total_of_account_amounts_is_grounded`, `test_a_changed_or_invented_number_is_not`,
`test_small_counts_years_and_nearby_dates_are_free`, `test_a_date_in_a_file_name_is_grounded`,
`test_a_number_before_a_slash_and_a_word_or_inside_a_name_is_grounded`, `test_corrupt_changes_one_number_from_the_tools`,
`test_the_response_has_the_tool_results_for_the_evaluation`,
`test_the_conformal_threshold_flags_at_least_one_minus_alpha_of_the_unfaithful_answers`,
`evals/judge.py` (each AUC with its 95 % Hanley–McNeil interval; `calibrate` on the test runs).

## R16 Comparisons

As a team, we want to know which parts of the design and which model earn their cost.

- `evals/compare.py` compares runs of the same cases: the passes with a 95 % Wilson interval, the
  tools, fallbacks, latency, tool calls per message, the measured cost, and, against a reference,
  the cases won and lost with the exact McNemar p.
- `evals/ablations.py` builds variants from the same parts as the app (one agent with every tool, no
  history, searches with no limit, a wrong number in the first reply, no reply agent) and runs a set
  with each; the app has no switch for it. It
  measures the cost of each run (the change of the key's usage, one run at a time).
- A hypothesis is committed before its run, with its test and its threshold, and its result is
  reported whether it holds or not. Each one is in `docs/experiments.md`.

Proof: `make compare`, `docs/experiments.md`, `evals/results/`.

## Out of scope

Real customer data and real logins, a contact point for the alerts, a relay from the webhooks to a
chat such as Telegram, streaming answers in `POST /chat`, a labelled set from Getnet's support team.
