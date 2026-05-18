"""OAuth credential management for pf-runtime communications connectors.

Cherry-pick from onyx-dot-app/onyx's `CredentialsProviderInterface` pattern.
Lets connectors hold a *refreshable* credential rather than a raw 60-minute
access token, eliminating the manual playground refresh loop.

See: .planning/post-phase-4-7-0/ONYX_CHERRYPICK.md §1.
"""
