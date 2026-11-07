"use strict";
const contractText = "FICTIONAL DEMONSTRATION ONLY\nPurchase Agreement\nThe fictional buyer purchases one unit of Model E equipment from the fictional seller.\nThe price is not agreed and will be negotiated after delivery.\nThe seller assumes unlimited liability for all losses.\nThis fictional purchase agreement is governed by mainland-China law.\n";
const stages = [
  {
    "label": "STAGE 01 / EXTRACTION",
    "title": "Locate the actual words.",
    "description": "The recorded extraction identifies a price clause and attaches its exact position in the normalized input.",
    "excerptLabel": "ORIGINAL CONTRACT EXCERPT · CHARACTERS 135–197",
    "excerpt": "The price is not agreed and will be negotiated after delivery.",
    "note": "The input has no numbered clauses. Optional section numbering is metadata; contract evidence remains tied to the original text."
  },
  {
    "label": "STAGE 02 / RISK",
    "title": "Surface a candidate concern.",
    "description": "The rule scan identifies affirmative unlimited-liability wording. This candidate is part of the recorded result, not a legal verdict.",
    "excerptLabel": "RECORDED RISK DESCRIPTION",
    "excerpt": "Potential unlimited liability wording (matched phrase: unlimited liability)",
    "note": "Source: “The seller assumes unlimited liability for all losses.” A phrase match does not determine enforceability, fairness, or the right commercial allocation."
  },
  {
    "label": "STAGE 03 / COMPLIANCE",
    "title": "Keep the source in view.",
    "description": "The recorded compliance stage proposes clarification of the expressly unagreed price. Its status remains needs_review.",
    "excerptLabel": "RECORDED ISSUE",
    "excerpt": "The price term is expressly left unagreed and deferred to post-delivery negotiation, so the contract does not state the price or a determinable pricing mechanism.",
    "sourceQuote": "合同生效后，质量、价款或者报酬、履行地点等内容没有约定或者约定不明确的，可以协议补充；不能达成补充协议的，按照合同相关条款或者交易习惯确定。",
    "sourceNote": "Civil Code Article 510 summary · original Chinese summary text, not a verbatim statute quotation. Citation identity is checked; legal interpretation still requires review.",
    "note": "Only three source summaries are available. English glosses are separate unreviewed translations and are not the citable text."
  },
  {
    "label": "STAGE 04 / SUGGESTION",
    "title": "Propose. Do not silently amend.",
    "description": "The recorded missing-information path offers an addition candidate. This is selected from the result; other generated revisions contained errors.",
    "excerptLabel": "RECORDED ADDITION CANDIDATE",
    "excerpt": "Consider adding terms for Price",
    "note": "The original trial also produced a draft that lost the supplied quantity. Later offline checks reject recognized fact loss. Suggestions remain proposals requiring party confirmation and legal review."
  }
];

const buttons = Array.from(document.querySelectorAll("[data-stage]"));
function showStage(index, focus = false) {
  const stage = stages[index];
  buttons.forEach((button, i) => {
    button.setAttribute("aria-selected", String(i === index));
    button.tabIndex = i === index ? 0 : -1;
  });
  document.getElementById("stage-panel").setAttribute("aria-labelledby", `tab-${index}`);
  for (const [id, value] of Object.entries({"stage-label": stage.label, "stage-title": stage.title,
    "stage-description": stage.description, "excerpt-label": stage.excerptLabel,
    "stage-excerpt": stage.excerpt, "stage-note": stage.note,
    "source-quote": stage.sourceQuote || "", "source-note": stage.sourceNote || ""})) {
    document.getElementById(id).textContent = value;
  }
  document.getElementById("source-box").hidden = !stage.sourceQuote;
  if (focus) buttons[index].focus();
}
buttons.forEach((button, index) => {
  button.addEventListener("click", () => showStage(index));
  button.addEventListener("keydown", event => {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % buttons.length;
    if (event.key === "ArrowLeft") next = (index + buttons.length - 1) % buttons.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = buttons.length - 1;
    if (next !== undefined) { event.preventDefault(); showStage(next, true); }
  });
});
document.getElementById("contract-text").textContent = contractText;
showStage(0);
