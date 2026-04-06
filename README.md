# Poetry to Anki

Turn poems into [Anki](https://apps.ankiweb.net) flashcard decks. Each card shows a 13-line window of the poem with one line blanked out — a *cloze deletion* — so you practice recalling the missing line in context. Shuffle through every line in every stanza until you have the poem memorized.

## How the cards work

Each card shows up to 13 consecutive lines of the poem. One line is hidden behind a cloze blank. The bottom of the card shows:

- Which stanza and line is being tested (e.g. *Stanza 2, Line 3*)
- Which lines are visible in the window (e.g. *Lines 5-17 of 30*)
- The poem title and author, year, and source link (when available)

By default, each stanza's lines are presented in a shuffled order, so consecutive reviews test different lines. Short poems (13 lines or fewer) always show the whole poem on every card.

---

## Installation

You need Python 3.13 or later and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone <this repo>
cd anki-poems
uv sync
```

All commands below are run from the `anki-poems` folder.

---

## Quickstart

1. Add a poem (see [Adding poems](#adding-poems) below).
2. Build the deck:
   ```bash
   python poetry_to_anki.py build
   ```
3. Open Anki. Go to **File → Import** and select the `poetry.apkg` file that was just created.

That's it. A new deck called **Poetry** (with a subdeck per poem) will appear in Anki.

---

## Adding poems

There are three ways to add a poem.

### Option 1 — Fetch from Poetry Foundation (easiest)

If the poem you want is on [poetryfoundation.org](https://www.poetryfoundation.org), copy its URL and run:

```bash
python fetch_poem.py https://www.poetryfoundation.org/poems/48860/the-raven
```

This downloads the poem, preserves indentation and italics, fills in the metadata (title, author, year, source URL), and saves a file to `poems/`. No manual editing required.

### Option 2 — Interactive prompt

For poems not on Poetry Foundation, run the guided script:

```bash
python add_new_poem.py
```

It asks for the title, author, and optional metadata, creates a file in `poems/`, and opens it in your text editor. Delete the placeholder line and paste your poem text.

### Option 3 — Create the file manually

Create a `.md` file anywhere inside `poems/`. The format is:

```
---
title: "The Tyger"
author: "William Blake"
collection: "Songs of Experience"
year: 1794
url: "https://www.poetryfoundation.org/poems/43687/the-tyger"
---

Tyger Tyger, burning bright,
In the forests of the night;
What immortal hand or eye,
Could frame thy fearful symmetry?

In what distant deeps or skies,
Burnt the fire of thine eyes?
```

**Rules:**
- The `---` block at the top is optional, but if present, `title` is required.
- `collection`, `year`, and `url` are optional.
- Blank lines separate stanzas. They appear as blank lines in the card window.
- Inline Markdown works in the poem body: `*italic*`, `**bold**`, `` `code` ``, `[link text](url)`.
- Leading spaces on a line are preserved — useful for indented lines.

---

## Building the deck

```bash
python poetry_to_anki.py build
```

This reads every `.md` file in `poems/` and creates `poetry.apkg`. Import that file into Anki.

To rebuild after adding or editing poems, run `build` again and re-import. Anki will update existing cards rather than creating duplicates (cards have stable IDs based on the poem's title, author, and source).

### Build options

| Option | Default | Description |
|--------|---------|-------------|
| `-f FILE …` | all files in `poems/` | Process only specific files |
| `--output FILE` | `poetry.apkg` | Name of the output file |
| `--deck-name NAME` | `Poetry` | Parent deck name in Anki |
| `--mode ankiconnect` | `apkg` | Send cards directly to a running Anki (see below) |
| `--no-shuffle` | shuffled | Test lines in order rather than randomly |
| `--single-deck` | individual decks | Put all poems in one flat deck instead of subdecks |
| `--no-wrap` | wrapped | Disable automatic line-wrapping |
| `--max-line-length N` | `50` | Wrap lines longer than N characters |
| `--multi-stanza` | off | Add extra cards that span two stanzas at once |

#### Examples

Process only one poem:
```bash
python poetry_to_anki.py build -f poems/edgar-allan-poe_the-raven.md
```

Use a custom deck name and output file:
```bash
python poetry_to_anki.py build --deck-name "My Poems" --output my-poems.apkg
```

Disable shuffling (lines tested in order):
```bash
python poetry_to_anki.py build --no-shuffle
```

Allow longer lines before wrapping:
```bash
python poetry_to_anki.py build --max-line-length 70
```

---

## Sending cards directly to Anki (AnkiConnect)

Instead of creating an `.apkg` file and importing it manually, you can send cards straight to a running Anki instance. This requires the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on.

1. Install AnkiConnect from the Anki add-on browser (code `2055492159`).
2. Restart Anki.
3. Run:
   ```bash
   python poetry_to_anki.py build --mode ankiconnect
   ```

Anki must be open while the command runs.

---

## Validating poem files

Check that all YAML frontmatter is well-formed before building:

```bash
python poetry_to_anki.py validate
```

Or validate specific files:

```bash
python poetry_to_anki.py validate -f poems/the-raven.md
```

This reports any files with missing required fields or malformed YAML without building a deck.

---

## Card and deck behavior in detail

**Line shuffling.** By default, each stanza's lines are presented in a different random order on each review pass. If a stanza has four lines, you'll see four cards per pass — one for each line — but in a shuffled order. The next time you review, a new shuffle is used. Disable with `--no-shuffle`.

**Individual subdecks.** Each poem gets its own subdeck under the parent deck (e.g. `Poetry::The Raven`). If two poems share a title, the author name is appended to distinguish them. Disable with `--single-deck`.

**13-line window.** Each card shows at most 13 lines. For poems longer than 13 lines, the window is centered on the cloze line and shifts at the beginning and end of the poem. Wrapped lines and blank stanza-break lines both count toward the 13.

**Multi-stanza cards.** The optional `--multi-stanza` flag generates additional cards that show two consecutive stanzas together (when each stanza has two or fewer logical lines). These cards test whether you can bridge the stanza boundary.

**Stable card IDs.** Cards are identified by poem title, author, and source URL (or file path if no URL is set). Re-running `build` and re-importing will update existing cards rather than creating new ones, preserving your review history.

---

## AI Statement

The code was largely written by Claude (Anthropic).
