# DOCTRINE — morning-logs

## One job

Create one safe daily operational briefing from Hermes runtime truth.

## Source order

1. Fleet ops status
2. Fleet pending approvals
3. Fleet recent events
4. Labyrinth health and guideposts
5. Sessions only when a guidepost points there
6. Logs only after Fleet/Labyrinth indicate a runtime issue
7. Cron for schedule/last-run confidence
8. Profiles for identity/scope drift
9. Docs for API mapping

## Safety doctrine

- No kill button.
- No token editor.
- No profile mutation.
- No approval execution.
- No deploys.
- No spending.
- No external sends.
- No raw secret, token, prompt, private message, or log dump in PFOS events.

## Promotion doctrine

Do not add Vercel, Supabase, GitHub, PostHog, Stripe, or business collectors until the core Hermes loop is useful for several runs. One workflow earns the next one.
