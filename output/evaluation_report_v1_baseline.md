# Evaluation report

Tickets evaluated: **50** (labelled by hand, never seen by the model). With this few tickets every percentage has a wide margin of error (see the intervals).

## Overall accuracy

- Category accuracy: **80.0% (40/50, 95% CI 67-89%)**  (baseline, always guess the most common category: 20%)
- Priority accuracy (exact): **58.0% (29/50, 95% CI 44-71%)**  (baseline, always guess the most common priority: 44%)
- Priority within one level: **92.0% (46/50, 95% CI 81-97%)**
- Category AND priority both correct: **46.0% (23/50, 95% CI 33-60%)**
- Priority bias: AI too high on 13 tickets, too low on 8 (average difference +0.10 levels; positive = AI rates tickets more serious than you did)

## Category accuracy by true category (your labels)

```
Billing & Payments     7/8  (88%)
Delivery & Shipping    10/10  (100%)
Returns & Refunds      3/4  (75%)
Account & Access       6/6  (100%)
Product Issue          8/9  (89%)
App & Website Issues   4/6  (67%)
General Inquiry        2/7  (29%)
```

## Category mistakes (you said -> AI said)

```
3x  General Inquiry  ->  Billing & Payments
1x  App & Website Issues  ->  Account & Access
1x  App & Website Issues  ->  Delivery & Shipping
1x  Billing & Payments  ->  Delivery & Shipping
1x  General Inquiry  ->  Product Issue
1x  General Inquiry  ->  Returns & Refunds
1x  Product Issue  ->  Returns & Refunds
1x  Returns & Refunds  ->  Product Issue
```

## Priority confusion matrix (rows = your label, columns = AI)

```
priority        Low  Medium  High  Urgent
human_priority                           
Low              11      10     0       1
Medium            2       5     1       1
High              0       2     7       0
Urgent            1       1     2       6
```

## Can the confidence score be trusted?

Accuracy here means category AND priority both correct. If confidence were reliable, accuracy would rise with it.

```
confidence below 0.80   tickets:  1   both correct: 100%
confidence 0.80 - 0.89  tickets:  2   both correct:   0%
confidence 0.90 - 0.94  tickets:  8   both correct:  50%
confidence 0.95 - 1.00  tickets: 39   both correct:  46%
```

Average stated confidence: 0.94. Actual both-correct rate: 0.46. Gap (overconfidence): +0.48

## What the human-review queue would look like at different thresholds

Tickets with confidence below the threshold go to a person. 'Auto' tickets are handled without review.

```
threshold  to review   auto    accuracy of auto tickets    accuracy of reviewed
0.70               0     50                         46%                       -
0.75               1     49                         45%                    100%
0.80               1     49                         45%                    100%
0.85               1     49                         45%                    100%
0.90               3     47                         47%                     33%
0.95              11     39                         46%                     45%
1.00              38     12                         58%                     42%
```

Current rule (confidence < 0.75 or similarity < 0.55) flagged 1 of 50 tickets.

## Does the best-matching SOP agree with the AI?

The SOP that retrieval ranked first belongs to a category. If it differs from the AI's category, that is a cheap warning sign (and it does not rely on the model's own confidence).

```
SOP category = AI category   tickets: 37   category correct:  78%   both correct:  46%
SOP category differs         tickets: 13   category correct:  85%   both correct:  46%
```

## Accuracy by retrieval similarity

```
similarity below 0.60      tickets:  1   category correct: 100%   both correct: 100%
similarity 0.60 - 0.64     tickets: 11   category correct:  82%   both correct:  55%
similarity 0.65 - 0.69     tickets: 23   category correct:  78%   both correct:  30%
similarity 0.70 and above  tickets: 15   category correct:  80%   both correct:  60%
```

## Category counts: your labels vs the AI

```
category                you   AI
Billing & Payments        8   10
Delivery & Shipping      10   12
Returns & Refunds         4    5
Account & Access          6    7
Product Issue             9   10
App & Website Issues      6    4
General Inquiry           7    2
```

## Mistakes: 27 tickets

Saved to output/eval_errors.csv, most confident mistakes first (the dangerous ones).