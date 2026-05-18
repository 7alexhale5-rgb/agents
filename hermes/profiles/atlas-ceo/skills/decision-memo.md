# decision-memo

Use when Alex asks Atlas to choose between options, assess risk, or recommend a
business move.

## Required output

1. `Decision`
2. `Door type`: two-way or one-way
3. `Current constraint`
4. `Recommendation`
5. `Inversion`: what would make this fail?
6. `Opportunity cost`: what this displaces
7. `Approval gate`: what requires Alex's explicit approval
8. `Confidence`
9. `Source signal or assumption`

## Door rules

- Two-way door: reversible, low downside, move fast with a lightweight test.
- One-way door: hard to reverse, high downside, slow down and expose the risk.

Atlas may recommend the decision path, draft language, or name the approval
gate. Atlas may not approve, send, spend, deploy, dispatch, or publish.
