# Experiments

What we tried to choose the design, the model and the checks, with the numbers and the files. Each
comparison runs the same cases; shares have a 95 % Wilson interval, and a comparison with a
reference has the cases won and lost with the exact McNemar p (`evals/compare.py`). Where we wrote a
hypothesis before a run, we give the time we wrote it; each result file has the time of its run in
its name.

Two changes split the runs in time, so tables never mix runs from both sides of them:

- **The parallel-call bug**: when the router called two agent tools in one step,
  each merged its own copy of the list of tool calls into the session, and the last one won. A tool
  call could vanish from `agents_used`, `tools_used` and the number check. Runs before the fix can
  miss a tool call where the router called agents at once. The first multi-source runs were void;
  they are in `evals/results/void/`.
- **The decision-model tag** (see below) replaced the LLM tagger.

## Models

The dev set (40 messages), same code, no fallback model; the cost is the measured change of the
OpenRouter key, one run at a time. Runs of 2026-11-09, before the bug fix.

| Model | Passed (95 % CI) | Fallbacks | p95 | US$ a message | Against DeepSeek: won / lost, p |
|---|---|---|---|---|---|
| `qwen/qwen3.7-flash` | 36/40 (77–96 %) | 1 | 116.7 s | 0.00076 | 0 / 2, p = 0.50 |
| `openai/gpt-oss-120b` | 34/40 (71–93 %) | 1 | 26.8 s | 0.00082 | 0 / 4, p = 0.12 |
| **`deepseek/deepseek-v4-flash-0731`** | **38/40** (83–99 %) | 0 | 29.9 s | 0.00098 | |

`uv run python -m evals.compare models`; the chart is `docs/cost-quality.svg`. No gap is significant
with 40 messages. DeepSeek lost no case to either and had no fallback; gpt-oss-120b is dominated.

## The design: agent tools against one agent

One agent with every tool and every prompt (`evals/ablations.py`), on the same cases.

| Run | Passed (95 % CI) | Tool calls a message | p50 / p95 | US$ a message | Against the agent tools: won / lost, p |
|---|---|---|---|---|---|
| Dev, before the fix: agent tools | 39/40 (87–100 %) | 2.5 | 12.6 / 37.4 s | | |
| Dev, before the fix: one agent | 38/40 (83–99 %) | 1.2 | 7.5 / 21.1 s | | 1 / 2, p = 1.00 |
| Dev, after the fix: agent tools | 38/40 (83–99 %) | 3.0 | 8.8 / 53.6 s | 0.00137 | |
| Dev, after the fix: one agent | 36/40 (77–96 %) | 1.2 | 5.8 / 22.9 s | 0.00080 | 0 / 2, p = 0.50 |
| Multi-source set (8): agent tools | 8/8 (68–100 %) | 8.2 | 24.4 / 42.3 s | | |
| Multi-source set (8): one agent | 8/8 (68–100 %) | 3.0 | 16.6 / 27.6 s | | 0 / 0, p = 1.00 |

- **Hypothesis H1** (written before its runs): on `evals/hard.jsonl`, 8 messages that need
  two or more sources at once, or one source after another, the agent tools pass more cases. With
  8 cases, only 6 to 0 or wider gives p < 0.05. **Result: no evidence** (8/8 against 8/8).
- Almost every dev difference is a tag, which is the same in every variant: it is run-to-run noise.
- On our data, one agent is as good and cheaper. We keep the agent tools because the challenge asks
  for a Router, a Knowledge and a Customer Support agent, and because a new agent is one file.

## Other models per agent

The design with agent tools, with another model or provider for some agents (2026-11-09 and 10,
after the fix). Reference: the agent tools on DeepSeek.

| Variant | Passed (95 % CI) | Fallbacks | p50 / p95 | US$ a message | won / lost, p |
|---|---|---|---|---|---|
| Agent tools, DeepSeek (reference) | 38/40 (83–99 %) | 0 | 8.8 / 53.6 s | 0.00137 | |
| One agent, DeepSeek | 36/40 (77–96 %) | 2 | 5.8 / 22.9 s | 0.00080 | 0 / 2, p = 0.50 |
| Specialists on `deepseek-v4.1-flash-1017` | 37/40 (80–97 %) | 2 | 10.3 / 40.6 s | 0.00135 | 1 / 2, p = 1.00 |
| Every agent on the fastest provider | 38/40 (83–99 %) | 0 | 9.1 / 42.6 s | 0.00140 | 0 / 0, p = 1.00 |
| Fastest providers, specialists on `gpt-oss-20b` | 37/40 (80–97 %) | 2 | 8.2 / 23.7 s | **0.00078** | 1 / 2, p = 1.00 |

- **Hypothesis H2** (written before its run): specialists on a model with cheaper input make the agent tools cheaper
  than one agent, with no loss of passes. **Result: no**: US$ 0.00135 against 0.00080. The specialist
  model's output costs 67 % more, and the agent tools make more calls.
- A latency benchmark (the same request, 5 times each): one DeepSeek call takes about 2 s, so the
  time of a message is the number of calls in a row; the provider with the lowest latency took
  1.6 s; `gpt-oss-20b` 1.7 s for 2.4 times less money; Qwen and gpt-5-nano about 4 s.
- **Hypothesis H3** (written before its runs): the fastest providers with `gpt-oss-20b` specialists make the agent
  tools cheaper and faster than the reference, with no loss of passes. **Result: yes**: −43 % cost,
  p95 54 → 24 s, 1 won and 2 lost (p = 1.00), at the cost of one agent. We did not adopt it: its two
  fallbacks are `gpt-oss-20b` answering as `support` without its tools; the check caught both, but
  each one sends a merchant to a person for nothing. We did not keep the variant code.

## The tag

The LLM tagger against a decision model (`microsoft/microsoft-decision-1`, one `choice` question
with the five tags and their criteria, no tuning), on the messages of the dev set and on the final
set, whose expected tags we wrote before any tagger ran on them.

| | Dev (40) | Final (10) | Same tag in two runs | US$ a message |
|---|---|---|---|---|
| Decision model | 39/40 (87–100 %) | 10/10 | 40/40, 10/10 | about 0.000005 |
| LLM tagger (DeepSeek), six runs | 37 to 39 /40 | 10/10 | varies | one model call |

Against each LLM run, the decision model won 1 or 2 cases and lost 0 or 1 (p ≥ 0.5): not more
accurate, but stable, cheaper, and with a probability. It replaced the LLM tagger.

## Faithfulness checks

Labels: 203 answers of eight runs, 28 of them not faithful, each "no" with its reason
(`evals/labels.jsonl`). We read each answer against every tool result of its message. A label counts
only for its run. `--corrupt` changes one number in each faithful answer of a final run.

| Check | Natural answers, first seven runs (23 of 164 not faithful) | Final + changed numbers (7 of 17) |
|---|---|---|
| Number check: caught / false alarms | 0/23, 0/141 | 7/7, 0/10 |
| Decision model: AUC (95 % CI, Hanley–McNeil) | 0.70 (0.58–0.83) | 1.00 |
| NLI per claim (mDeBERTa-XNLI), first 54 labels: AUC | 0.61 to 0.76 | 0.56 (0.28–0.85) |
| LLM judge listing unsupported claims (`gpt-5-mini`), first 34 labels | up to 17 false alarms in 29 | |

- **The number check** is the gate in the API. Over every saved answer, it caught 458 of 475 changed
  numbers (94–98 %) and stopped none of 1,063 sent answers. In the API it stopped one invented
  contract clause, and a few good answers before four fixes (a date in a file name, a phone number
  with an en dash, a number before "/mês", the total of two amounts of the previous answer), each with a test. It caught none of the 23 natural
  faults: none of them is a wrong number.
- **The NLI check** did not earn its place: the site writes in the imperative ("Aceite…"), and answers
  join passages or infer. We removed its code; the numbers are in `evals/results/nli-claims-20261109.json`.

### The triage threshold: split conformal prediction

The decision model ranks the answers, but a ranking does not say how many to read. The first threshold
(0.975, picked on one dev run) flagged 7 of 10 faithful final answers. Now the threshold comes from
split conformal prediction (`uv run python -m evals.judge calibrate`):

- **Calibration**: the 114 labelled answers of the five runs of 2026-11-09, 15 not faithful. With
  ALPHA = 0.2, the threshold is the 13th smallest P(faithful) of the 15 (ceil(16 × 0.8)): 0.9954. A
  guarantee of 90 % needs 9 or more unfaithful answers for each one missed; with 15, 0.9988.
- **Test**: the 89 labelled answers of the three runs of 2026-11-10, from later code, 13 not faithful.
  The third run also has the H4 prompts, which the judge reads as its instructions: a harder test.

| On the test runs (89 answers) | Value |
|---|---|
| Unfaithful answers flagged | 9/13 (42–87 %) |
| Faithful answers flagged | 32/76 (32–53 %) |
| Answers to read | 41/89 (46 %) |
| Unfaithful answers that reading 41 of 89 at random finds, on average | 6.0 of 13 |
| AUC on the test runs | 0.71 (0.54–0.88) |

- What the guarantee says: if the unfaithful answers of a run are exchangeable with the calibration
  ones, each is flagged with a chance of at least 80 %, on average over calibration sets. 9 of 13
  (69 %) is below the target but inside its interval: 13 answers cannot show a miss of this size.
  Before the H4 prompts, 6 of 8; with them, 3 of 5.
- What it does not say: nothing about one run, about answers of a new model or prompt (they need new
  labels), or about the faithful answers: the share of them flagged is a measured cost, not a bound.
- The decision model is deterministic for the tag, but its P(faithful) changed a little between two
  judge runs of the same answers (AUC 0.80 and 0.79 on the first dev labels), which is one more
  reason for a margin.
- What the triage is worth: a person reads half of the answers and finds about 70 to 80 % of the
  faults that no automatic check finds, instead of about half. When the prompts change, label a new
  run and recalibrate.

### The faults that no check catches

From our labels, the same few patterns come back:

- 4020-4011, the line to order a Get Smart, given as the support line;
- the cardholder's rule (an accepted chargeback is credited) given to the merchant;
- the rent discounts ("até R$ 14,90" off) read as the new rent;
- causes of a decline that no source gives;
- a person who answers "with priority" or "today";
- "capitais e regiões metropolitanas" for "capitals"; the phone hours given to WhatsApp.

## The prompts: channel facts and cases

The labels showed that some faults start in our own prompt: it gave the phone as "4002-4000
(capitals)", but the sources say "4002-4000 or 4003-4000, capitals and metropolitan regions;
0800-648-8000, other places", and they give WhatsApp 11 97694-6815. The router prompt also invited
"the same tool more than once".

- **Hypothesis H4** (written before its run): with the channels
  from the sources in the router prompt, "call each agent once, with every question it must
  answer", and a rule in the knowledge prompt
  (give each fact to its case: the cardholder is not the merchant, a discount is not a price, one
  machine is not another; give no cause, step or channel the results do not give), one dev run has
  fewer unfaithful answers than the run of the code before (`dev-20261110-002355`, 8 of 40 by our
  labels), with no fewer passes than 38 of 40 and no more than 3.05 tool calls a message.
  Primary measure: unfaithful answers, paired by case, exact McNemar. With 40 cases, only a change
  of about 6 to 0 or more is significant. Risk: we label the new answers knowing they are new; we use
  the same rules as for the old ones, and every "no" has its reason.
- **Result: no evidence** (`dev-20261110-101614`). Unfaithful answers: 5 of 39 (6–27 %) against
  8 of 40 (10–35 %); paired, 4 cases better and 1 worse, p = 0.38. Passes 37 of 40 (80–97 %), below
  the criterion of 38: one fallback (the router sent a homework request to knowledge, which declined
  with no tool, so the answer check stopped it) and one search on the web instead of the base. Tool
  calls 2.42 a message, 2 repeated or blocked: no change.
- The rent discounts were read right this time; the chargeback rule, the causes of a decline and a
  rule of another machine came back, and one answer turned the two capital lines into one general
  line and one for capitals.
- We keep the channels: they correct a fact of our prompt against the sources, not a measured gain.

## Prompt injection

The decision call of the tag also answers a yes-or-no question: does the message try to change the
instructions, get them, give a new role, speak as Getnet staff or the system, or get another
merchant's data? `evals/injection.py` scores public attacks and normal messages
(`injection-20261113-100651`, about US$ 0.006). The limit is split conformal on 154 of the 309 FAQ
questions (alpha 0.01): P(injection) above 0.3208.

| Set | Flagged (95 % CI) |
|---|---|
| Attacks in Portuguese (Weni/prompt-injections-1.0.0, from HackAPrompt) | 235/300 (73–83 %) |
| Attacks in English and German (deepset/prompt-injections, test) | 37/60 (49–73 %) |
| Our three dev injections | 3/3 |
| The other 155 FAQ questions | 1/155 (0–4 %): "Como funciona a Superdigital?" |
| Our dev and final messages | 0/47 |
| Normal texts of the deepset test | 0/56 (0–6 %) |

- Most attacks that pass ask the model to print a phrase ("I have been PWNED") in a hidden form:
  letters between slashes, binary, emojis, a word cut in two. They do not ask for data or a role.
- The guarantee assumes that new normal messages are like FAQ questions; merchant messages are not,
  so the 0/47 on our own messages matters more. A real false alarm sends a merchant to a person, not
  to a refusal.

## Plan again after the check

When the answer check stops an answer (numbers that no tool gave, or an agent with no tool call), the
flow runs once more, and the router gets the reason; only then does a person take over. In our runs
the check stops very few answers (11 fallbacks in 861 saved answers, almost all in variants), so
natural runs cannot measure the gain. We measure it with a fault that we inject.

- **Hypothesis H5** (written before its run): `evals/ablations.py wrong-number` adds 7 to the first
  number of the first reply to each dev message that has a number. Of the answers that the check
  stops, the second run gives an answer that passes the check in at least 80 %. Primary measure:
  the share of stopped answers with no fallback, with its Wilson 95 % interval. Also reported: the
  passes of the dev checks, and the extra time of a replan (p50 of the stopped messages against
  the same messages in the last dev run). Without the replan, each stopped answer is a ticket.
- **Result: holds** (`ablation-wrong-number-20261113-101912`, US$ 0.077). The check stopped 12
  answers; the second run gave a checked answer for all 12 (95 % CI 76–100 %), and all 12 passed
  the dev checks. No fallback in the run; 37 of 40 passed (the misses: "O que é gravame?" from the
  web, and two injections tagged `backoffice`; this run was before the injection stop). A replan
  costs time: p50 26.6 s for the stopped messages against 20.3 s for the same messages in the last
  dev run. 30 of the 40 sent answers have a number, so the check stopped fewer than half of the
  changes: the change often hits a step number or a count up to 10, which the check lets through.
  The run measures the replan, not the check (the run did not record which answers it changed).

## Latency: one writer fewer

A message waits for its model calls in a row, and three of them write a long text: the knowledge
agent, the router (an internal answer) and the reply agent. In the last dev run the slow messages
were the ones with more calls and longer answers (median 13.3 s, p95 41.0 s).

- **Hypothesis H6** (written before its runs): with no reply agent, and the reply rules in the
  router prompt (`evals/ablations.py router-replies`), the dev p95 is at least 25 % lower than the
  p95 of the real design in a run just before it, with no more than one pass fewer (paired, exact
  McNemar) and no answer in the wrong language. The two runs go back to back, so that the
  provider's speed is about the same for both.
- **Result: no** (`ablation-baseline-20261113-103103`, then `ablation-router-replies-20261113-103806`).
  p95 31.1 → 25.2 s (−19 %, below the 25 % of the criterion); p50 10.4 → 7.4 s (−29 %). Passes 39/40
  against 39/40, 0 won and 0 lost; every English message got an English answer; US$ 0.036 against
  0.041 for the run. We keep the reply agent. Neither design reaches a p95 of 20 s: the slowest
  messages wait for a support agent that asks the knowledge agent, three writers in a row.
- The baseline run is also the dev run of the current code: 39/40, and the three injections went to
  a person, as they must.

## Ablations of the design

Before the bug fix, same day, back to back (US$ 0.18 for the four).

| Variant | Passed (95 % CI) | Passed, tags aside | Tool calls a message | Repeated or blocked calls | won / lost, p |
|---|---|---|---|---|---|
| The real design | 39/40 (87–100 %) | 40/40 | 2.5 | 3 | |
| No history in the router | 36/40 (77–96 %) | 39/40 | 2.5 | 2 | 0 / 3, p = 0.25 |
| Searches with no limit | 38/40 (83–99 %) | 40/40 | 3.0 | 8 | 0 / 1, p = 1.00 |

- No history: the one real loss is a second ticket for a request that had one. The follow-up checks
  then were too weak (which tools were called); they now also check a fact of the answer.
- Searches with no limit: more calls and almost three times as many repeated or blocked calls, with
  no change in passes or latency that this set can show. An earlier claim of ours (p95 from 49 s to
  26 s) compared runs at different times; this controlled run does not support it.

## Retrieval

| Set | hit@1 | hit@3 | hit@6 (95 % CI) | MRR |
|---|---|---|---|---|
| Our 27 questions | 19 | 26 | 27/27 (88–100 %) | 0.82 |
| The site's 309 FAQ questions, Portuguese (we did not write them) | 277 | 297 | 302/309 (95–99 %) | 0.93 |
| The same, translated to English by the model | 138 | 240 | 265/309 (81–89 %) | 0.62 |

The knowledge agent writes its queries in Portuguese, so English queries are a test of the
embeddings more than of the agent.
