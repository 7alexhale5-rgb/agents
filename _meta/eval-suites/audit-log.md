# audit-log.md — VanClief append-only audit trail

VanClief writes one entry per audit. Never edited; only appended.

Format per entry:

```
## YYYY-MM-DD HH:MM ET — <event>
- profile: <name>
- severity: P0 | P1 | P2 | clean
- finding: <one-line>
- action: <what VanClief did>
- pr_draft: <link or "none">
```

## Recent

(Empty until VanClief runs its first audit.)
