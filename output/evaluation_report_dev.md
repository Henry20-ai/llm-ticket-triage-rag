# Evaluation report (dev set)

Tickets evaluated: **50** (labelled by hand, never seen by the model). Prompt version(s) in these results: v2. With this few tickets every percentage has a wide margin of error (see the intervals).

## Overall accuracy

- Category accuracy: **86.0% (43/50, 95% CI 74-93%)**  (baseline, always guess the most common category: 20%)
- Priority accuracy (exact): **58.0% (29/50, 95% CI 44-71%)**  (baseline, always guess the most common priority: 44%)
- Priority within one level: **92.0% (46/50, 95% CI 81-97%)**
- Category AND priority both correct: **48.0% (24/50, 95% CI 35-61%)**
- Priority bias: AI too high on 16 tickets, too low on 5 (average difference +0.22 levels; positive = AI rates tickets more serious than you did)

## Real Urgent tickets

- You labelled 10 tickets Urgent. The AI also said Urgent on 8; it rated 2 lower (the dangerous direction).
- The AI said Urgent on 2 tickets you did not label Urgent (extra work, but safe).

## Category accuracy by true category (your labels)

```
Billing & Payments     8/8  (100%)
Delivery & Shipping    10/10  (100%)
Returns & Refunds      2/4  (50%)
Account & Access       6/6  (100%)
Product Issue          9/9  (100%)
App & Website Issues   6/6  (100%)
General Inquiry        2/7  (29%)
```

## Category mistakes (you said -> AI said)

```
3x  General Inquiry  ->  Billing & Payments
2x  General Inquiry  ->  Product Issue
2x  Returns & Refunds  ->  Product Issue
```

## Priority confusion matrix (rows = your label, columns = AI)

```
priority        Low  Medium  High  Urgent
human_priority                           
Low               8      13     0       1
Medium            1       6     1       1
High              0       2     7       0
Urgent            1       1     0       8
```

## Can the confidence score be trusted?

Accuracy here means category AND priority both correct. If confidence were reliable, accuracy would rise with it.

```
confidence 0.80 - 0.89  tickets:  1   both correct: 100%
confidence 0.90 - 0.94  tickets:  7   both correct:  29%
confidence 0.95 - 1.00  tickets: 42   both correct:  50%
```

Average stated confidence: 0.96. Actual both-correct rate: 0.48. Gap (overconfidence): +0.48

## Does the best-matching SOP agree with the AI?

```
SOP category = AI category   tickets: 36   category correct:  81%   both correct:  50%
SOP category differs         tickets: 14   category correct: 100%   both correct:  43%
```

## Accuracy by retrieval similarity

```
similarity below 0.60      tickets:  1   category correct: 100%   both correct:   0%
similarity 0.60 - 0.64     tickets: 11   category correct:  73%   both correct:  36%
similarity 0.65 - 0.69     tickets: 23   category correct:  91%   both correct:  43%
similarity 0.70 and above  tickets: 15   category correct:  87%   both correct:  67%
```

## Category counts: your labels vs the AI

```
category                you   AI
Billing & Payments        8   11
Delivery & Shipping      10   10
Returns & Refunds         4    2
Account & Access          6    6
Product Issue             9   13
App & Website Issues      6    6
General Inquiry           7    2
```

## Human-review rules compared

Flagged = sent to a person. 'Mistakes caught' = share of wrong answers that were flagged. 'Urgent missed' = real Urgent tickets the AI rated lower AND did not flag (the dangerous ones). The more tickets a rule flags, the less work the AI saves, so this is a trade-off, not a single best answer.

```
rule                                         flagged  mistakes caught  Urgent missed  unreviewed accuracy
v1: low confidence / weak match               0 (0%)             0/26           2/10             48% (50)
predicted High/Urgent                       18 (36%)             3/26           2/10             28% (32)
category Billing & Payments                 11 (22%)             5/26           0/10             46% (39)
CURRENT RULE: priority or category          23 (46%)             8/26           0/10             33% (27)
current rule + SOP category differs         33 (66%)            15/26           0/10             35% (17)
```

Rules were chosen after reading mistakes on the dev set, so judge them on the test set, not here.

## Mistakes: 26 tickets

Saved to output/eval_errors_dev.csv, most confident mistakes first (the dangerous ones).