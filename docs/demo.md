# English demo guide

## Scope

English-language purchase/sale contracts; mainland-China law only; knowledge cutoff 2026-10-20. Canadian-law processing is future work. All examples are fictional. English is the interface and analysis language, not a choice of jurisdiction.

## Offline demonstration

From `python/`, with the virtual environment active:

```sh
python -m src.cli --mock --file ../examples/purchase-complete.txt
python -m src.cli --mock --file ../examples/purchase-missing-price.txt
python -m src.cli --mock --text ''
```

The first example should complete with no missing-information candidates under the limited presence heuristics. That does not establish legal sufficiency or a risk-free contract. The second illustrates an unlimited-liability candidate, missing-price information, a draft suggestion, and an exact original Chinese source-summary citation with a separate English gloss. The third rejects empty input with exit code 1.

`--mock` substitutes scripted model responses. The Runner, agents, retrieval, source matching, and result validation execute, but the findings do not demonstrate model reasoning or model accuracy. The output explicitly marks `mock: true`. CLI exits: 0 success, 2 partial, 1 failed/invalid input, 124 timed out.

## Live mode

A configured model provider can be invoked by replacing `--mock` with `--real`. Text is sent to that provider and charges may apply. A two-input fictional live rerun completed both workflows after optional-numbering and compliance-scope fixes. It also exposed a capped-liability category error and a revision that lost a supplied quantity. Subsequent consistency checks have only been tested offline. Do not present offline output as a live model result. Use only fictional or authorized data.

The web interface calls live backend processing; it does not include an offline-mode selector. The submission response includes the full result; it is not stored as backend review history. Refresh clears the result shown in the browser. Start both services using the README, paste an example, and submit only after configuring and approving the model budget.

## Reading compliance candidates

The compliance stage proposes drafting/completeness clarifications only and keeps `overall_compliance=needs_review`. Source summaries are not a basis for broad legal-invalidity or mandatory-rule claims. Obvious scope violations are isolated with a `COMPLIANCE_SCOPE_REJECTED` diagnostic and `partial` execution, even if their quotation matches a source. `out_of_scope_findings` is displayed explicitly in the interface; do not describe a rejected concern as a validated finding.

The screen is conservative English phrase matching, not semantic verification. It can miss paraphrases or factual errors and can reject benign wording. A passing citation check shows source membership and quote identity, not that a source proves the model's conclusion. This limitation also applies to the prior currency-omission overstatement. The risk and suggestion stages still require human scrutiny; narrowing compliance does not certify their reasoning.

For a timed walkthrough, commands and interview questions, see the [English presentation script](presentation.md).

## Presentation outline

“This project demonstrates a fixed four-agent workflow for contract review: extraction, risk, compliance candidates, and suggestions. A shared Runner serves the API and CLI. Request budgets, retries, and timeout diagnostics make failures visible. Retrieval selects a small set of applicable source summaries, and citations must match sources from the current run. The demo processes English purchase-contract text within a mainland-China legal scope. Its source coverage and legal evaluation remain limited.”

Show the input, `status`, `missing_clauses`, a contract evidence span, and a knowledge citation. Explain that `success` measures workflow completion; it does not certify legality. Avoid system-wide accuracy or improvement claims.

### Conservative consistency checks

An unlimited-liability model finding that contradicts recognized capped or negated wording stops the risk stage with an explicit error. An affirmative uncapped obligation elsewhere in the same clause is retained for review. This phrase check does not resolve parties, exceptions, cross-clause obligations, or every form of liability wording.

Proposed revisions must retain detected numeric tokens, common numeric periods/quantities, common currency codes, and English quantities such as “one unit.” Comma formatting such as 1000/1,000 is normalized. Missing or changed values fail the suggestion stage and produce a partial result; rejected drafts are not shown as successful revisions. New or changed commercial terms are explicitly labeled as proposals requiring party confirmation and legal review. The model is instructed to preserve other supplied facts and mark new terms individually, but runtime checks do not prove it complied.

These lexical checks can reject legitimate rewording or intentional numeric changes. They can also miss changed names, unsupported legal assertions, altered relationships, or numbers retained in the wrong context. Added terms are not validated as legally necessary or appropriate. Source text and evidence are preserved separately; examine the diff and seek human review. No additional repair requests are made.
