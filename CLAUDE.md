# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_windowing.py -v

# Build the Anki deck (outputs poetry.apkg)
python poetry_to_anki.py build

# Send directly to a running Anki instance (requires Anki + AnkiConnect addon)
python poetry_to_anki.py build --mode ankiconnect

# Validate YAML frontmatter only
python poetry_to_anki.py validate

# Add a new poem interactively
python add_new_poem.py
```

Package manager is `uv`. To add/remove dependencies, use `uv add`/`uv remove`.

## Architecture

This tool converts poetry `.md` files into Anki cloze-deletion flashcard decks.

**Data flow:**
```
poems/*.md → parse_metadata() → parse_stanzas() → wrap_long_lines()
           → build_global_poem() → NoteBuilder.build_notes()
           → render_windowed_cloze() → genanki.Note → .apkg / AnkiConnect
```

**Module responsibilities:**
- `poetry_core.py` — All parsing, rendering, and note-building logic. This is the core.
- `poetry_cli.py` — CLI argument parsing, file I/O, AnkiConnect communication.
- `poetry_to_anki.py` — Backward-compatible re-export shim; don't add logic here. Tests import `build_notes` from here.
- `add_new_poem.py` — Standalone interactive script for adding new poem files.
- `fetch_poem.py` — Scrapes a poem from poetryfoundation.org and writes a ready-to-use `.md` file to `poems/`.
- `poetry_errors.py` — Exception hierarchy (`PoetryToAnkiError` → `FileProcessingError`, `ConfigurationError`, `AnkiConnectError`).

**Key concepts in `poetry_core.py`:**
- **13-line windowing:** Each card shows a 13-line context window centered on the cloze line, shifting at poem boundaries.
- **GlobalPoem / LineEntry:** Unified poem representation across stanzas with stable logical line keys for GUID generation.
- **GUID stability (critical):** `make_guid()` is keyed to `(stanza_index, logical_line_index)` — independent of shuffle order — so cards survive re-generation. `MODEL_ID` in `poetry_core.py` is a fixed constant; changing it or changing `compute_poem_key()` logic will orphan all existing Anki cards.
- **`Config` dataclass:** Controls shuffle, wrapping, multi-stanza cards, etc. All processing options flow through here.
- **`NoteBuilder`:** Has three note-building paths: shuffled (default), sequential, and multi-stanza.

**Poem file format:**

```
---
title: "Poem Title"       # Required if YAML present
author: "Author Name"
collection: "Book Name"   # optional
year: 1794                # optional
url: "https://..."        # optional
---

First stanza line one
First stanza line two

Second stanza (blank line = stanza break)
```

Inline Markdown (emphasis, links, code spans) is supported in poem bodies. HTML is sanitized via `bleach` to `em`, `strong`, `code`, `a` tags only.
