# Local English presentation

## What this presentation demonstrates

A fixed four-agent contract-review workflow with shared execution controls, source matching, and visible failures. English purchase/sale text is processed within a mainland-China scope, with a knowledge cutoff of 2026-10-20. Canadian-law processing is future work.

Use the offline CLI walkthrough below for a repeatable presentation without a provider key. Say explicitly that its model responses are scripted. The earlier real-provider trial is separate evidence; the current consistency policy has only been tested offline. Do not introduce the CLI simulation as live model reasoning.

## 90-second introduction

“This project explores how to make a small contract-review workflow inspectable. It accepts pasted text or UTF-8 TXT and runs four fixed stages: extraction, risk identification, compliance candidates, and revision suggestions.

The CLI and API share a Runner. A request budget, bounded retries, and timeouts control model calls. Extracted clauses point to exact positions in the input. The compliance stage retrieves from three applicable Chinese Civil Code summaries, and citations must match original summary text from that review. English glosses are separate, unreviewed translations.

The demo handles English purchase contracts under mainland-China law. English input does not imply Canadian-law support. Compliance output is limited to drafting and completeness candidates, with human review required.

Today I’m showing an offline simulation: the workflow and validation run, while model responses are scripted. A separate two-contract live trial completed both workflows but exposed semantic errors. Subsequent offline checks reject some obvious contradictions and fact loss. Completion and matching citations do not establish legal accuracy.”

## Five-minute walkthrough

### 1. Establish the scope — 30 seconds

Show the README scope and the two fictional TXT files. Explain that a “complete” filename means the presence heuristics find no missing fields, not that the contract is legally sufficient.

“Both examples are fictional. The system supports short text and TXT, not PDF, Word, or OCR. This is a local engineering demonstration; it is not a legal-advice service.”

### 2. Show the fixed workflow — 45 seconds

Show the architecture diagram in the README.

“The four agents have separate processing responsibilities. LangGraph fixes their order; they do not autonomously choose tools or plan the workflow. The API and CLI share the same Runner rather than implementing separate review logic.”

Point to `python/src/pipeline/runner.py`, `python/src/pipeline/graph.py`, and `python/src/harness/execution.py` if asked for code. Describe these as repository components; do not imply a particular personal authorship history.

### 3. Run the missing-information example — 90 seconds

From the repository root, after completing the README installation:

```sh
cd python
source .venv/bin/activate
python -m src.cli --mock --file ../examples/purchase-missing-price.txt
```

Start by pointing to `mock: true`. Inspect these fields inside `result`:

| Field | What to explain |
| --- | --- |
| `status` | `success` means the required workflow completed, not that the contract is safe. |
| `missing_clauses` | Presence heuristics propose missing information, including price; they do not establish legal requirements. |
| `risk_findings` | The scripted example includes an unlimited-liability candidate. |
| `evidence` | The quote matches the input slice at `start` and `end`; offsets refer to normalized text. |
| `knowledge_citations` | The original Chinese source-summary quotation is retained; the English gloss is not the citable source. |
| `suggestions` | Proposed drafts and additions require confirmation; they are not automatic edits. |
| `diagnostics` | Stage attempts and execution details make failures inspectable; simulated usage is not provider billing. |

On the checked version, this command returned exit 0, one risk candidate and seven suggestions. Those counts belong to the scripted example, not an evaluation metric. Six missing-information candidates included Price, Performance period, Delivery method, Quality standard, Acceptance terms and Dispute resolution.

### 4. Show the contrast and input failure — 45 seconds

In the same terminal:

```sh
python -m src.cli --mock --file ../examples/purchase-complete.txt
python -m src.cli --mock --text ''
```

The checked complete example returned exit 0 with no missing-information candidates, no risk findings and no suggestions in this simulation. The empty-input command returned exit 1 and `EMPTY_TEXT`.

“An empty findings list from a scripted model is not evidence that a real contract has no risk. The rejected input shows the application reports an error instead of pretending a review completed.”

### 5. Explain the real trial and remaining limits — 90 seconds

“A separate real-provider run processed these same two fictional contracts through all four stages. It used eight requests with no retries. The complete example took about 20.5 seconds and the missing-price example about 17.8 seconds. Those are two observations, not a performance benchmark.

Reviewing the output found that the risk model labeled an explicitly capped liability clause as unlimited liability. A proposed revision also replaced the supplied one-unit quantity with a placeholder. We preserved those failures. Current offline checks reject those saved outputs rather than silently correcting their labels or accepting the drafts.

A risk-stage contradiction stops downstream processing. A suggestion-stage validation failure returns a partial result. The checks are conservative lexical rules: they can reject legitimate rewording and miss other factual or legal errors. A source quote matching exactly does not prove its interpretation. Wider legal coverage and professional validation remain outside this demo.”

Close with: “The demonstrated result is an inspectable workflow with bounded execution and explicit limitations. Legal reliability still requires much more evidence and review.”

## Optional local web walkthrough

The interface has no offline-mode selector. Submitting a contract sends it to the configured provider and may incur charges. Do not submit during this presentation without a separately agreed provider and request budget. Unused capacity from an earlier trial is not permission for another run.

To inspect the interface locally without submitting a review, use two terminals after installation and local configuration:

```sh
# Terminal 1: from the repository root
cd python
source .venv/bin/activate
APP_HOST=127.0.0.1 python -m src.api.main
```

```sh
# Terminal 2: from the repository root
cd frontend
npm run dev -- --hostname 127.0.0.1
```

Open http://localhost:3000. Keep both services on loopback; do not use a public tunnel or deployment. Stop each process with Ctrl-C. Startup alone does not demonstrate successful current live processing. If a future live submission is approved, show its actual status and any failure, rather than switching to scripted output without disclosure.

The API returns results directly without backend review history. The browser holds results until refresh or a new submission. CLI files are saved only with an explicit `--output`. Model-provider retention policies are separate from application storage.

## Interview questions

**Why multiple agents?** Each stage has a separate prompt and output responsibility. Their sequence is fixed, which makes stage failures easier to locate. This version does not demonstrate autonomous planning or parallel execution.

**What does grounding guarantee?** Retrieval applies scope filters and citations must match this run’s sources. Those checks establish source identity, not semantic correctness or legal applicability of every assertion.

**Why keep Chinese quotations?** They preserve the reviewed source summaries. English glosses help explain them but are labeled unreviewed translations; they are not exact statutory text.

**What prevents runaway calls?** A shared per-review cap of eight attempts, one retry for transient errors, SDK retries disabled, a 30-second per-call limit and a 120-second review deadline. Local timeout does not guarantee provider cancellation or refunds. There is no global concurrency limit.

**Why stateless?** This testing version returns each review directly and avoids retaining backend results. It has no history, resume or recovery feature. Statelessness does not mean external providers retain nothing.

**How strong is the evaluation?** The candidate passed 130 offline software tests. Two fictional inputs completed an earlier live policy; semantic review exposed errors. The latest consistency policy has not been rerun live. Neither test count nor workflow completion is an accuracy measure.

**What did you personally build?** Explain the design decisions, implementation changes, and validation evidence you can substantiate. Describe your personal contributions accurately.

**What comes next?** Wider evaluation, semantic consistency checks and legal review are possible future work. Canadian-law processing would be a separate future path. Public hosting, authentication and production safeguards are not implemented commitments.
