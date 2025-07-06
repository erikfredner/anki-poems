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
```

## File Naming

Place `.txt` files in the `poems/` directory using either:

- `title.txt` (author will be "Unknown")
- `Author Name::Title.txt` (author and title parsed from filename)

## Features

- Each stanza becomes multiple cloze cards (one per line)
- Notes are tagged with `title:slug` and `author:slug` for easy filtering
- Support for both .apkg export and live AnkiConnect integration
- Stable IDs prevent duplicate cards on re-import