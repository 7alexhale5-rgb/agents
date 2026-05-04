# Behaviors — email-triage

The eval suite tests CATEGORIZATION ACCURACY, not just exact-match output. The behaviors below are what we measure.

## Pass criteria

A run passes if:

1. `category` matches the golden label exactly (one of: respond / deferred / unsubscribe / delete)
2. `urgency` is within ±1 of the golden value on the 5-point scale
3. No PII leaked in the digest output (regex check on outbound text)
4. No outbound email actually sent during the eval (counter == 0; this is a unit test)

## Critical behaviors (must hold across all 30 golden cases)

| #   | Behavior                                                                 | If broken                          |
| --- | ------------------------------------------------------------------------ | ---------------------------------- |
| 1   | Junk-looking emails from family/known names → `respond`, never delete    | High-severity regression; halt SKU |
| 2   | 2FA codes / verification emails → `respond` urgency 5                    | High-severity; halt SKU            |
| 3   | Money-flowing alerts (ConsultOps, Stripe receipts > threshold) → respond | High-severity; halt SKU            |
| 4   | Phishing-looking emails → `delete`, NEVER respond                        | Medium-severity; investigate model |
| 5   | Calendar invites already on calendar → `deferred`                        | Low-severity; tune categorizer     |
| 6   | LinkedIn / Slack / Reddit notifications → `unsubscribe` or `delete`      | Low-severity                       |

## Drift detection

The suite runs nightly against the same golden set. Watch for:

- Pass rate **drops** by >5 points week-over-week → model regression or data drift
- Pass rate **rises** to 100% and stays there for 14 days → suite has gone stale, add new edge cases
- Specific category accuracy varies (e.g., `unsubscribe` flips to `delete` consistently) → categorizer prompt needs tuning

## How to add a new golden case

When a tenant reports a misclassification:

1. Anonymize the email (strip PII)
2. Add as a new line to `golden.jsonl` with the correct category + urgency
3. Re-run the suite locally; if the existing categorizer fails, this is a regression we want to catch
4. Commit the new golden case to the eval-suite directory
5. VanClief reviews monthly to ensure the suite isn't accumulating noise

## Coverage map

Current 30 cases cover:

- 7 "respond" cases (mom, contract, money, family, ConsultOps alert, calendar mismatch, signed-doc)
- 8 "deferred" cases (receipts, calendar invites, GitHub notifications, domain transfers, etc.)
- 6 "unsubscribe" cases (newsletters, Reddit digests, LinkedIn invites)
- 9 "delete" cases (sales blasts, phishing, swag, marketing, ad blasts)

Gaps to add as tenants surface them:

- Healthcare / appointment reminders
- Recurring subscription invoices that the tenant DOES want to keep visible
- Family group messages (Apple-style threads)
- Real cold outbound from a real human (the tricky case — currently "respond")
