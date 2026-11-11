# Evaluation report (test set)

Tickets evaluated: **40** (labelled by hand, never seen by the model). Prompt version(s) in these results: v2. With this few tickets every percentage has a wide margin of error (see the intervals).

## Overall accuracy

- Category accuracy: **85.0% (34/40, 95% CI 71-93%)**  (baseline, always guess the most common category: 28%)
- Priority accuracy (exact): **62.5% (25/40, 95% CI 47-76%)**  (baseline, always guess the most common priority: 48%)
- Priority within one level: **80.0% (32/40, 95% CI 65-90%)**
- Category AND priority both correct: **52.5% (21/40, 95% CI 37-67%)**
- Priority bias: AI too high on 6 tickets, too low on 9 (average difference -0.15 levels; positive = AI rates tickets more serious than you did)

## Real Urgent tickets

- You labelled 9 tickets Urgent. The AI also said Urgent on 5; it rated 4 lower (the dangerous direction).
- The AI said Urgent on 3 tickets you did not label Urgent (extra work, but safe).

## Category accuracy by true category (your labels)

```
Billing & Payments     8/9  (89%)
Delivery & Shipping    7/7  (100%)
Returns & Refunds      2/3  (67%)
Account & Access       4/4  (100%)
Product Issue          10/11  (91%)
App & Website Issues   2/4  (50%)
General Inquiry        1/2  (50%)
```

## Category mistakes (you said -> AI said)

```
2x  App & Website Issues  ->  Delivery & Shipping
1x  Billing & Payments  ->  App & Website Issues
1x  General Inquiry  ->  Product Issue
1x  Product Issue  ->  Account & Access
1x  Returns & Refunds  ->  Product Issue
```

## Priority confusion matrix (rows = your label, columns = AI)

```
priority        Low  Medium  High  Urgent
human_priority                           
Low               7       1     0       0
Medium            3      11     2       3
High              1       1     2       0
Urgent            1       3     0       5
```

## Can the confidence score be trusted?

Accuracy here means category AND priority both correct. If confidence were reliable, accuracy would rise with it.

```
confidence 0.90 - 0.94  tickets:  4   both correct:  75%
confidence 0.95 - 1.00  tickets: 36   both correct:  50%
```

Average stated confidence: 0.96. Actual both-correct rate: 0.53. Gap (overconfidence): +0.44

## Does the best-matching SOP agree with the AI?

```
SOP category = AI category   tickets: 33   category correct:  82%   both correct:  48%
SOP category differs         tickets:  7   category correct: 100%   both correct:  71%
```

## Accuracy by retrieval similarity

```
similarity below 0.60      tickets:  2   category correct: 100%   both correct:  50%
similarity 0.60 - 0.64     tickets:  7   category correct:  86%   both correct:  71%
similarity 0.65 - 0.69     tickets: 24   category correct:  83%   both correct:  38%
similarity 0.70 and above  tickets:  7   category correct:  86%   both correct:  86%
```

## Category counts: your labels vs the AI

```
category                you   AI
Billing & Payments        9    8
Delivery & Shipping       7    9
Returns & Refunds         3    2
Account & Access          4    5
Product Issue            11   12
App & Website Issues      4    3
General Inquiry           2    1
```

## Human-review rules compared

Flagged = sent to a person. 'Mistakes caught' = share of wrong answers that were flagged. 'Urgent missed' = real Urgent tickets the AI rated lower AND did not flag (the dangerous ones). The more tickets a rule flags, the less work the AI saves, so this is a trade-off, not a single best answer.

```
rule                                         flagged  mistakes caught  Urgent missed  unreviewed accuracy
v1: low confidence / weak match               0 (0%)             0/19            4/9             52% (40)
predicted High/Urgent                       12 (30%)             6/19            4/9             54% (28)
category Billing & Payments                  8 (20%)             4/19            0/9             53% (32)
CURRENT RULE: priority or category          16 (40%)            10/19            0/9             62% (24)
current rule + SOP category differs         21 (52%)            10/19            0/9             53% (19)
```

Rules were chosen after reading mistakes on the dev set, so judge them on the test set, not here.

## How often do two humans agree?

Tickets labelled by both of you: **40**. Where two people disagree there is no single 'correct' answer, so the human agreement rate is a realistic ceiling for the AI.

- Category agreement (you vs second labeller): **72.5% (29/40, 95% CI 57-84%)**, Cohen's kappa 0.66
- Priority agreement (exact): **65.0% (26/40, 95% CI 50-78%)**, within one level 80.0% (32/40, 95% CI 65-90%), Cohen's kappa 0.51
- AI vs the second labeller: category 85.0% (34/40, 95% CI 71-93%), priority 65.0% (26/40, 95% CI 50-78%)

## Mistakes: 19 tickets

Saved to output/eval_errors_test.csv, most confident mistakes first (the dangerous ones).