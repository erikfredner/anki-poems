# Poetry to Anki

Convert plain-text poems into Anki cloze deletion cards where each stanza becomes multiple notes (one blanked-out line per note) with full-stanza answers.

## Setup

```bash
# The environment is already configured with uv
source .venv/bin/activate
```

## Usage

```bash
# Create an .apkg file from all poems in the poems/ directory
python poetry_to_anki.py -f poems/*.txt --mode apkg

# Send directly to a running Anki instance (requires AnkiConnect)
python poetry_to_anki.py -f poems/*.txt --mode ankiconnect

# Process specific files
python poetry_to_anki.py -f poems/sonnet.txt poems/ode.txt --mode apkg

# Disable transition cards between stanzas
python poetry_to_anki.py -f poems/*.txt --mode apkg --no-transitions
```

## File Format

Place `.txt` files in the `poems/` directory. You can use either:

### YAML Frontmatter (Recommended)

```yaml
---
title: "The Tyger"
author: "William Blake"
collection: "Songs of Experience"
year: 1794
---

Your poem content here...
```

### Filename-based (Fallback)

- `title.txt` (author will be "Unknown")
- `Author Name::Title.txt` (author and title parsed from filename)

**Note**: YAML frontmatter takes precedence over filename parsing when both are present.

## Card Format

The generated cards use a clean, poetry-friendly format:

### Line Cloze Cards

- **Question**: Shows the stanza with one line hidden as a cloze deletion
- **Answer**: Reveals only the missing line, preserving the poem's formatting
- **Metadata**: Displays poem title, author, and stanza/line number
- **Styling**: Uses serif font and centered text for better readability

### Transition Cards (New!)

- **Question**: Shows the last line(s) of one stanza and prompts for the first line of the next
- **Answer**: Reveals the connecting line to help memorize stanza flow
- **Purpose**: Helps memorize the transitions and overall structure of the poem
- **Tagging**: Includes "transition" tag for easy filtering

## Features

- **Rich Metadata**: YAML frontmatter support for title, author, collection, and year
- **Beautiful Formatting**: Cards display as `"Title" by Author from <i>Collection</i> (Year)`
- **Two Card Types**: Line cloze cards + transition cards between stanzas
- **Transition Cards**: Help memorize the flow between stanzas (can be disabled with `--no-transitions`)
- Each stanza becomes multiple cloze cards (one per line)
- **Preserved formatting**: Line breaks are maintained in the card display
- **Clean answers**: Only the cloze deletion is revealed, not the entire stanza
- **Proper metadata**: Cards display the correct poem title and author with collection info
- Notes are tagged with `title:slug` and `author:slug` for easy filtering
- Support for both .apkg export and live AnkiConnect integration
- Stable IDs prevent duplicate cards on re-import
