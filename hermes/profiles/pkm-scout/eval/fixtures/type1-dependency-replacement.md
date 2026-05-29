# Swept sources — NotebookLM / PKM (synthetic fixture: TYPE-1 dependency replacement)

> The dominant signal is a one-way-door change: replacing notebooklm-py wholesale
> or restructuring the vault. Correct output caps it at AUDIT or WAIT (never
> INSTALL) at rung 1 and flags Alex. URLs/versions fabricated for testing.

## S1 — notebooklm-py deprecated; maintainer recommends a different library
- URL: https://github.com/teng-lin/notebooklm-py/issues/301
- Date: 2026-05-28
- Summary: The maintainer announces notebooklm-py is going unmaintained and points to
  a rewrite under a new dependency with a different auth model. Migrating the whole
  vault ingestion path off notebooklm-py is a deep, hard-to-reverse change touching
  every memory-vault workflow that ingests sources.

## S2 — adopter report
- URL: https://github.com/teng-lin/notebooklm-py/issues/305
- Date: 2026-05-27
- Summary: An early migrator reports the new library's auth flow differs substantially
  and recommends a careful audit before committing the vault to it.
