# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run a single test file
uv run python -m pytest tests/test_windowing.py -v

# Build the Anki deck (outputs poetry.apkg)
uv run anki-poems build

# Send directly to a running Anki instance (requires Anki + AnkiConnect addon)
uv run anki-poems build --mode ankiconnect

# Validate YAML frontmatter only
uv run anki-poems validate

# Add a new poem interactively
uv run anki-poems-add

# Fetch a poem from poetryfoundation.org into poems/
uv run anki-poems-fetch <url>
```

Package manager is `uv`. To add/remove dependencies, use `uv add`/`uv remove`.
The project installs as an editable package (`uv sync`); the `anki-poems`,
`anki-poems-add`, and `anki-poems-fetch` console scripts map to
`anki_poems.cli:main`, `anki_poems.add_poem:main`, and
`anki_poems.fetch_poem:main`. The same entry points are reachable via
`python -m anki_poems[.add_poem|.fetch_poem]`.

## Architecture

This tool converts poetry `.md` files into Anki cloze-deletion flashcard decks.

**Data flow:**
```
poems/*.md → parse_metadata() → parse_stanzas() → wrap_long_lines()
           → build_global_poem() → NoteBuilder.build_notes()
           → render_windowed_cloze() → genanki.Note → .apkg / AnkiConnect
```

The source package lives under `src/anki_poems/` (standard src layout).

**Module responsibilities:**
- `src/anki_poems/core.py` — All parsing, rendering, and note-building logic. This is the core.
- `src/anki_poems/cli.py` — CLI argument parsing, file I/O, AnkiConnect communication.
- `src/anki_poems/__init__.py` — Public API: re-exports core/cli names and convenience wrappers (`build_notes`, `parse_poem`, etc.). Tests import `build_notes` from `anki_poems`.
- `src/anki_poems/__main__.py` — `python -m anki_poems` entry point → `cli.main()`.
- `src/anki_poems/add_poem.py` — Standalone interactive script for adding new poem files.
- `src/anki_poems/fetch_poem.py` — Scrapes a poem from poetryfoundation.org and writes a ready-to-use `.md` file to `poems/`.
- `src/anki_poems/errors.py` — Exception hierarchy (`PoetryToAnkiError` → `FileProcessingError`, `ConfigurationError`, `AnkiConnectError`).

**Key concepts in `core.py`:**
- **13-line windowing:** Each card shows a 13-line context window centered on the cloze line, shifting at poem boundaries.
- **GlobalPoem / LineEntry:** Unified poem representation across stanzas with stable logical line keys for GUID generation.
- **GUID stability (critical):** `make_guid()` is keyed to `(stanza_index, logical_line_index)` — independent of shuffle order — so cards survive re-generation. `MODEL_ID` in `core.py` is a fixed constant; changing it or changing `compute_poem_key()` logic will orphan all existing Anki cards.
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
