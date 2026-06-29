# Codex Instructions

You are working on the Institutional Bounce Platform.

Before making any changes:

1. Read:
   - docs/PROJECT_MANIFEST.md
   - README.md

2. Never violate the architecture.

Architecture:

GUI
↓
Controllers
↓
Services
↓
DatabaseManager
↓
SQLite

Business logic belongs only inside Services.

Indicators perform calculations only.

DatabaseManager performs persistence only.

Controllers connect UI to Services.

GUI never performs calculations.

Never use print().

Use logging.

Always preserve existing functionality.

If changing multiple files, explain exactly why each file changed.

Application must always compile before completion.

Never modify more than one architectural layer unless explicitly instructed.

Example:

Database issue?

Only modify:

database/

Do not modify:

controllers/

services/

ui/

unless required.

If another layer must change,
explain why before making changes.