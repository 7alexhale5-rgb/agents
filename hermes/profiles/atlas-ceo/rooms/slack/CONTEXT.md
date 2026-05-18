# Slack Room Context — atlas-ceo

Status: active bring-up path

Atlas uses Slack as an Alex-first DM surface. The first supported behavior is a
plain text DM reply to Alex through the PF Runtime Slack adapter.

## Current scope

- DM-only
- Text-only
- Alex-only
- No slash commands
- No public channel posting
- No files, buttons, reactions, or workflow actions

## Completion gate

Slack is considered ready for the next Atlas capability only after PF Runtime can
load the profile, Slack auth succeeds, and Atlas posts a live smoke message to
Alex.
