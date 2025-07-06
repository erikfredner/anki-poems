# Poetry to Anki

Convert plain-text poems into Anki cloze deletion cards where each stanza becomes multiple notes (one blanked-out line per note) with full-stanza answers.

## Setup

```bash
# The environment is already configured with uv
source .venv/bin/activate
```

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
=== Poetry to Anki - Add New Poem ===

* Poem title: The Road Not Taken
* Author name: Robert Frost
Collection/Book name: Mountain Interval
Publication year: 1916
Source URL: https://www.poetryfoundation.org/poems/44272/the-road-not-taken

✓ Created file: poems/the-road-not-taken.md
✓ File opened in editor

# Add your poem text, then:
python poetry_to_anki.py  # Generate cards including the new poem
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

The generated cards use a clean, poetry-friendly format:

### Line Cloze Cards

- **Question**: Shows the stanza with one line hidden as a cloze deletion
- **Answer**: Reveals only the missing line, preserving the poem's formatting
- **Metadata**: Multi-line format showing title, author, collection, source, and line being tested
- **Styling**: Uses EB Garamond font (with serif fallback), left-justified text, clean layout
- **Whitespace Preservation**: All original indentation and spacing is preserved using `<pre>` tags with custom CSS that maintains the EB Garamond typography

### Transition Cards

- **Question**: Shows the last line(s) of one stanza and prompts for the first line of the next
- **Answer**: Reveals the connecting line to help memorize stanza flow
- **Purpose**: Helps memorize the transitions and overall structure of the poem
- **Tagging**: Includes "transition" tag for easy filtering
- **Whitespace Preservation**: Also preserves original formatting and indentation

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

- **Rich Metadata**: YAML frontmatter support for title, author, collection, year, and source URL
- **Source Tracking**: URLs display as clickable links on cards for easy reference
- **Beautiful Formatting**: Cards display as `"Title" by Author from <i>Collection</i> (Year)`
- **Individual Poem Decks**: Each poem gets its own subdeck for focused study (`--individual-decks`, default)
- **Line Shuffling**: Multiple review passes with random line selection to prevent answer leakage (default)
- **Transition Cards**: Optional cards to help memorize stanza-to-stanza flow (enabled with `--no-shuffle`)
- **Flexible Organization**: Study individual poems or select the parent deck to study all poems together
- **Two Card Types**: Line cloze cards + transition cards between stanzas
- **Transition Cards**: Help memorize the flow between stanzas (can be disabled with `--no-transitions`)
- **Stanza Shuffling**: Randomize stanza order during review to prevent answer leakage (`--shuffle-stanzas`)
- Each stanza becomes multiple cloze cards (one per line)
- **Preserved formatting**: Line breaks are maintained in the card display
- **Clean answers**: Only the cloze deletion is revealed, not the entire stanza
- **Proper metadata**: Cards display the correct poem title and author with collection info
- Notes are tagged with `title:slug` and `author:slug` for easy filtering
- Support for both .apkg export and live AnkiConnect integration
- Stable IDs prevent duplicate cards on re-import
