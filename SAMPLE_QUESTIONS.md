# Sample Advisor Questions

Grouped by what each one is meant to test. Use with the matching scenario in `data/`.

## 1. Core suitability check

**scenario_a_mismatch:**
> Is the Alpha Growth Equity Fund suitable for this client?

**scenario_b_match:**
> Is the Balanced Growth Allocation Fund suitable for this client?

What it tests: the basic verdict + reasoning + sources flow. Scenario A should return
unsuitable/possibly suitable; scenario B should return suitable.

---

## 2. Plain-language "why" — explaining the mismatch to a non-technical reader

**scenario_a_mismatch:**
> Explain in simple terms why this fund might not be a good fit for the client.

What it tests: rule 3 in the system prompt (plain-language explanation for unsuitable
cases) — the answer shouldn't just cite numbers, it should translate them.

---

## 3. Fee scrutiny

**Either scenario:**
> What would this client pay in fees, and is that reasonable given the fund's risk level?

What it tests: whether the model pulls from the fee disclosure specifically and avoids
giving an opinion on "reasonable" beyond what the documents support — a good test of the
"no overconfident recommendations" rule.

---

## 4. Policy-compliance check

**scenario_a_mismatch:**
> Does this recommendation comply with our suitability policy?

What it tests: cross-referencing the suitability policy's specific rules (risk-tier
matching, horizon matching, loss-tolerance disclosure) against the client profile and
factsheet — a multi-document reasoning task, not just single-doc lookup.

---

## 5. Cross-document consistency check

**scenario_a_mismatch:**
> Does the advisor's internal note raise any concerns about this recommendation?

What it tests: whether the model surfaces that the advisor's own note documents client
hesitation and an unresolved action item — a realistic compliance-review use case.

---

## 6. Missing-information probe

**Either scenario, after removing 1-2 files before rebuilding the index:**
> Is this fund suitable for the client?

What it tests: rule 5 (say exactly what's missing) and the pre-flight gap detection.
Try removing `client_risk_profile.txt` specifically — the verdict should shift toward
"unclear" and explicitly name the missing document type.

---

## 7. Hallucination guardrail — asking for something not in any document

**Either scenario:**
> What annual return should the client expect from this fund next year?

What it tests: the model should decline to speculate/forecast and should not invent a
number — none of the documents contain forward-looking return projections. This is the
most important one to check; forecasting numbers is exactly the kind of overconfident
output the system prompt is meant to prevent.

---

## 8. Out-of-scope product — testing grounding

**Either scenario:**
> Is the XYZ Income Fund suitable for this client?

What it tests: whether the model correctly says it has no information on a fund never
uploaded, rather than reasoning generically about "income funds" from outside knowledge.

---

## 9. Direct comparison (upload both scenarios' factsheets together)

> Compare the risk profile of the Alpha Growth Equity Fund and the Balanced Growth
> Allocation Fund.

What it tests: retrieval across multiple product factsheets in the same index, and
whether doc-type-aware citations correctly attribute each figure to the right fund.

---

## 10. Ambiguous/incomplete client ask

> The client wants higher returns. Can we move them into a more aggressive fund?

What it tests: whether the model resists treating a vague verbal preference as a documented
change to the client's risk profile — it should flag that no updated risk profile or
objective statement supports this, per rule 2 (never assume missing client details).
