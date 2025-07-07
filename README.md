# Poetry to Anki

Convert plain-text poems into Anki cloze deletion cards where each stanza becomes multiple notes (one blanked-out line per note) with full-stanza answers.

## Usage

1. Clone this repo.
2. `python add_new_poem.py` to add poems of your choosing to `poems/`
3. `python poetry_to_anki.py` to generate `poetry.apkg`
4. Import `poetry.apkg` into [Anki desktop](https://apps.ankiweb.net/).
5. Memorize poems!
6. Optional, but recommended: Install [EB Garamond](https://github.com/georgd/EB-Garamond).

## AI Statement

[Claude Sonnet 4](https://www.anthropic.com/claude/sonnet) generated most of this code, as well as the documentation below. I designed, prompted, and tested the implementation.

## Adding New Poems

Use the interactive script to easily add new poems with proper metadata:

```bash
python add_new_poem.py
```

This will:

1. Prompt you for poem metadata (title, author, collection, year, source URL)
2. Validate your input (year range, URL format)
3. Generate a safe filename from the title and author
4. Create a properly formatted `.md` file with YAML frontmatter in the `poems/` directory
5. Open the file in your default text editor for you to add the poem text

**Example workflow:**

```bash
$ python add_new_poem.py
Poetry to Anki - Add New Poem
========================================

Enter poem information (* = required):
* Poem title: The Road Not Taken
* Author name: Robert Frost
Collection/Book name: Mountain Interval
Publication year: 1916
Source URL: https://www.poetryfoundation.org/poems/44272/the-road-not-taken

✓ Created: poems/the-road-not-taken.md
✓ Title: The Road Not Taken | Author: Robert Frost | Collection: Mountain Interval | Year: 1916 | Source: https://www.poetryfoundation.org/poems/44272/the-road-not-taken
✓ Opened in editor

Next: Add poem text, save, then run 'python poetry_to_anki.py'
```

## Usage

```bash
# Create an .apkg file from all poems in the poems/ directory (default behavior)
python poetry_to_anki.py

# Specify output file name
python poetry_to_anki.py --output my_poems.apkg

# Send directly to a running Anki instance (requires AnkiConnect)
python poetry_to_anki.py --mode ankiconnect

# Process specific files instead of all .md files in poems/
python poetry_to_anki.py -f poems/sonnet.md poems/ode.md

# Disable line shuffling and use old behavior (one card per line + transitions)
python poetry_to_anki.py --no-shuffle

# Put all poems in a single deck instead of individual subdecks
python poetry_to_anki.py --single-deck

# Generate additional multi-stanza cards (two successive stanzas with clozes)
python poetry_to_anki.py --multi-stanza

# Disable line wrapping (keep original long lines)
python poetry_to_anki.py --no-wrap

# Adjust line wrapping length (default: 50 characters for mobile-friendly display)
python poetry_to_anki.py --max-line-length 65
```

## File Format

Place `.md` files in the `poems/` directory. You can use either:

### YAML Frontmatter (Recommended)

```yaml
---
title: "The Tyger"
author: "William Blake"
collection: "Songs of Experience"
year: 1794
url: "https://www.poetryfoundation.org/poems/43687/the-tyger"
---

Your poem content here...
```

**Whitespace Preservation**: All leading whitespace and indentation in your poem is automatically preserved. The tool wraps each stanza in `<pre>` tags and styles them with the same EB Garamond font for consistent typography.

**Line Wrapping**: By default, lines longer than 50 characters are automatically wrapped at word boundaries for optimal mobile display. Continuation lines are indented with 4 additional spaces. Use `--no-wrap` to disable or `--max-line-length` to adjust the threshold.

**Available fields:**

- `title`: Poem title (required)
- `author`: Poet's name (required)  
- `collection`: Book/collection name (optional)
- `year`: Publication year (optional)
- `url` or `source`: Source URL (optional, displays as clickable link)

### Filename-based (Fallback)

- `title.md` (author will be "Unknown")
- `Author Name::Title.md` (author and title parsed from filename)

**Note**: YAML frontmatter takes precedence over filename parsing when both are present.

## Card Format

The generated cards use a clean, poetry-friendly format optimized for both desktop and mobile devices:

### Line Cloze Cards

- **Question**: Shows the stanza with one line hidden as a cloze deletion
- **Answer**: Reveals the complete stanza with the missing line filled in
- **Metadata**: Multi-line format showing title, author, collection, source, and line being tested
- **Styling**: Uses EB Garamond font (with serif fallback), left-justified text, clean layout
- **Whitespace Preservation**: All original indentation and spacing is preserved using `<pre>` tags with custom CSS
- **Mobile Optimization**: Lines are automatically wrapped at 50 characters by default for portrait mode viewing

### Transition Cards

- **Question**: Shows the last line(s) of one stanza and prompts for the first line of the next
- **Answer**: Reveals the connecting line to help memorize stanza flow
- **Purpose**: Helps memorize the transitions and overall structure of the poem
- **Tagging**: Includes "transition" tag for easy filtering
- **Whitespace Preservation**: Also preserves original formatting and indentation

### Multi-Stanza Cards (Optional)

- **Purpose**: Shows two successive stanzas together with one cloze deletion to help understand inter-stanza relationships
- **Format**: Displays stanzas 1-2, 3-4, 5-6, etc. with exactly one line blanked out from either stanza
- **Example**: One card might show stanzas 1 and 2 with only line 2 of stanza 1 as a cloze deletion
- **Benefits**: Helps memorize longer passages and understand how stanzas connect thematically
- **Tagging**: Includes "multi-stanza" tag for easy filtering
- **Enable**: Use `--multi-stanza` flag to generate these additional cards alongside regular single-stanza cards

### Line Shuffling (Default)

- **Problem**: When reviewing cards in order, you see the answer to upcoming cards while solving the current one
- **Solution**: By default, the tool creates multiple review passes where each pass shows one random line blanked from each stanza
- **Effect**: You read through the entire poem multiple times (once per max stanza length), with different lines blanked each time
- **Benefits**: Preserves poem structure and stanza order while preventing answer leakage
- **Example**: For a 4-line poem with 2 stanzas, you get 4 review passes × 2 stanzas = 8 cards total
- **Trade-off**: Transition cards are automatically disabled since the blanked lines are randomized
- **Disable**: Use `--no-shuffle` to create one card per line in order (enables transition cards)

### Deck Organization

- **Individual Subdecks (Default)**: Each poem gets its own subdeck under `Poetry::<Poem Title>`
- **Benefits**: Study individual poems or select the parent deck to study all poems together
- **Navigation**: In Anki, you can choose "The Tyger" to study only Blake's poem, or "Poetry" to study all poems
- **Collision Handling**: If multiple poems have the same title, the author is automatically appended (e.g., "Poetry::Sonnet 18 (Shakespeare)")
- **Single Deck Mode**: Use `--single-deck` to put all poems in one `Poetry` deck like the old behavior
- **Flexibility**: Switch between modes depending on how you want to organize your study sessions

## Features

### Card Generation & Format

- **Cloze Deletion Cards**: Each stanza becomes multiple cards with one line blanked out per card
- **Line Shuffling (Default)**: Creates multiple review passes with random line selection to prevent answer leakage
- **Transition Cards**: Optional cards to help memorize stanza-to-stanza flow (enabled with `--no-shuffle`)
- **Multi-Stanza Cards**: Optional cards showing two successive stanzas with clozes (enabled with `--multi-stanza`)
- **Mobile-Optimized Display**: Lines automatically wrap at 50 characters for portrait mode viewing
- **Typography**: Beautiful EB Garamond font with serif fallbacks and preserved whitespace formatting

### Metadata & Organization

- **Rich YAML Frontmatter**: Support for title, author, collection, year, and source URL
- **Individual Poem Decks**: Each poem gets its own subdeck for focused study (default behavior)
- **Flexible Deck Organization**: Study individual poems or select parent deck to study all together
- **Source Tracking**: URLs display as clickable links on cards for easy reference
- **Smart Tagging**: Notes tagged with `title:slug` and `author:slug` for easy filtering
- **Collision Handling**: Automatically appends author names for poems with identical titles

### Technical Features

- **Dual Output Modes**: Export to `.apkg` files or send directly to Anki via AnkiConnect
- **Stable Card IDs**: Prevents duplicate cards when re-importing updated poem collections
- **Interactive Poem Addition**: `add_new_poem.py` script with validation and automatic file generation
- **Preserved Formatting**: All original indentation, line breaks, and spacing maintained using `<pre>` tags
- **Configurable Line Wrapping**: Adjust wrap length or disable entirely for different display preferences
