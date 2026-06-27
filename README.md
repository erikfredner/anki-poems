# Poetry to Anki

Turn poems into [Anki](https://apps.ankiweb.net) flashcard decks. Each card shows the full poem with one word blanked out — a *cloze deletion* — and opens scrolled to the blanked word, so you practice recalling the missing word in its full context. Work through every word in every line until you have the poem memorized.

## How the cards work

Each card shows the entire poem inside a scrollable box. One word is hidden behind a cloze blank, and the card automatically scrolls so the cloze line is centered when the card opens (and re-centers when you flip to the answer). The bottom of the card shows:

- Which stanza, line, and word is being tested (e.g. *Stanza 2, Line 3, Word 1*)
- The poem title and author, collection/year, and source link (when available)

By default, the cards within each consecutive ~13-line span of the poem are introduced in a shuffled order, so you don't simply march word-by-word from top to bottom. The spans themselves stay in poem order. Use `--no-shuffle` to introduce every word in strict reading order instead.

The auto-scroll relies on a small script in the card template. On clients with limited JavaScript (e.g. AnkiWeb), the full poem still renders and you can scroll to the blank manually.

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
   uv run anki-poems build
   ```

3. Open Anki. Go to **File → Import** and select the `poetry.apkg` file that was just created.

That's it. A new deck called **Poetry** (with a subdeck per poem) will appear in Anki.

---

## Adding poems

There are three ways to add a poem.

### Option 1 — Fetch from Poetry Foundation (easiest)

If the poem you want is on [poetryfoundation.org](https://www.poetryfoundation.org), copy its URL and run:

```bash
uv run anki-poems-fetch https://www.poetryfoundation.org/poems/48860/the-raven
```

This downloads the poem, preserves indentation and italics, fills in the metadata (title, author, year, source URL), and saves a file to `poems/`. No manual editing required.

### Option 2 — Interactive prompt

For poems not on Poetry Foundation, run the guided script:

```bash
uv run anki-poems-add
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
- Blank lines separate stanzas. They appear as blank lines on the card.
- Inline Markdown works in the poem body: `*italic*`, `**bold**`, `` `code` ``, `[link text](url)`.
- Leading spaces on a line are preserved — useful for indented lines.

---

## Building the deck

```bash
uv run anki-poems build
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
| `--no-shuffle` | shuffled | Introduce cards in strict poem order instead of shuffling within each span |
| `--single-deck` | individual decks | Put all poems in one flat deck instead of subdecks |
| `--no-wrap` | wrapped | Disable automatic line-wrapping |
| `--max-line-length N` | `50` | Wrap lines longer than N characters |
| `--multi-stanza` | off | Add extra cards that span two stanzas at once |

#### Examples

Process only one poem:

```bash
uv run anki-poems build -f poems/edgar-allan-poe_the-raven.md
```

Use a custom deck name and output file:

```bash
uv run anki-poems build --deck-name "My Poems" --output my-poems.apkg
```

Disable shuffling (cards introduced in reading order):

```bash
uv run anki-poems build --no-shuffle
```

Allow longer lines before wrapping:

```bash
uv run anki-poems build --max-line-length 70
```

---

## Sending cards directly to Anki (AnkiConnect)

Instead of creating an `.apkg` file and importing it manually, you can send cards straight to a running Anki instance. This requires the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on.

1. Install AnkiConnect from the Anki add-on browser (code `2055492159`).
2. Restart Anki.
3. Run:

   ```bash
   uv run anki-poems build --mode ankiconnect
   ```

Anki must be open while the command runs.

---

## Validating poem files

Check that all YAML frontmatter is well-formed before building:

```bash
uv run anki-poems validate
```

Or validate specific files:

```bash
uv run anki-poems validate -f poems/the-raven.md
```

This reports any files with missing required fields or malformed YAML without building a deck.

---

## Card and deck behavior in detail

**Card order.** Every word in every line becomes its own card. By default, the cards within each consecutive ~13-line span of the poem are shuffled together, so the order in which new cards are introduced jumps around the span instead of marching word-by-word from the top. The spans themselves stay in poem order. Use `--no-shuffle` to introduce cards in strict reading order (line 1 word 1, line 1 word 2, … then line 2, and so on).

**Individual subdecks.** Each poem gets its own subdeck under the parent deck (e.g. `Poetry::The Raven`). If two poems share a title, the author name is appended to distinguish them. Disable with `--single-deck`.

**Full poem with cloze-anchored scroll.** Each card shows the whole poem in a scrollable box and opens centered on the cloze line, re-centering when you reveal the answer. The auto-scroll uses a small script in the card template; where JavaScript is restricted (e.g. AnkiWeb) the full poem still renders and you scroll to the blank yourself.

**Multi-stanza cards.** The optional `--multi-stanza` flag generates additional cards that show two consecutive stanzas together (when each stanza has two or fewer logical lines). These cards test whether you can bridge the stanza boundary.

**Stable card IDs.** Cards are identified by poem title, author, and source URL (or file path if no URL is set). Re-running `build` and re-importing will update existing cards rather than creating new ones, preserving your review history.

---

## AI Statement

The code was largely written by [Claude 4.6 Sonnet](https://www.anthropic.com/news/claude-sonnet-4-6).
