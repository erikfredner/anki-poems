# Poetry to Anki

Create Anki cloze cards from poems. Each card shows a 13‑line window through the poem (stanza breaks and wrapped lines count), with one line hidden as the cloze. The cloze is centered when possible and shifts near the poem’s start/end. Poems with 13 lines or fewer show the full poem on every card.

## Quickstart

1. Add poems to `poems/` (run `python add_new_poem.py` if you want a guided template).
2. Build an `.apkg`:
   `python poetry_to_anki.py build`
3. Import `poetry.apkg` into Anki.

## File Format

Poems are Markdown files. Optional YAML frontmatter is supported:

```
---
title: "The Tyger"
author: "William Blake"
collection: "Songs of Experience"
year: 1794
url: "https://www.poetryfoundation.org/poems/43687/the-tyger"
---

Tyger Tyger, burning bright, 
...
```

If YAML is present, `title` is required. Inline Markdown (emphasis, strong, links, code) is rendered and sanitized. Line wrapping is on by default (50 chars) and counts toward the 13‑line window. Blank or whitespace‑only lines split stanzas and appear as a blank line in the window.

## CLI

```
python poetry_to_anki.py build                  # Build poetry.apkg (default)
python poetry_to_anki.py validate               # Validate YAML frontmatter
python poetry_to_anki.py build --mode ankiconnect
python poetry_to_anki.py build -f poems/a.md poems/b.md
python poetry_to_anki.py build --no-shuffle-stanzas
python poetry_to_anki.py build --single-deck
python poetry_to_anki.py build --no-wrap-lines
python poetry_to_anki.py build --max-line-length 65
python poetry_to_anki.py build --multi-stanza
```

## Card & Deck Behavior

- **Windowing:** 13 lines per card; cloze centered when possible.
- **Line shuffling:** Enabled by default; creates review passes with random cloze lines per stanza.
- **Multi‑stanza cards (optional):** Adds extra cards across pairs of stanzas when both stanzas have two or fewer lines.
- **Decks:** Each poem gets its own subdeck by default; use `--single-deck` to combine.
- **Stable GUIDs:** Based on title/author plus source URL (if present) or file path.

## Output

- `build` creates `poetry.apkg` or sends notes via AnkiConnect.
- `validate` checks YAML frontmatter (title required if YAML exists).

## AI Statement

The code was largely written by OpenAI's Codex.
