#!/usr/bin/env python
"""
Poetry to Anki CLI Tool

Converts plain-text poems into Anki cloze deletion cards where each stanza 
becomes multiple notes (one blanked-out line per note) with full-stanza answers.
"""
import argparse
import html
import re
import random
from pathlib import Path
from slugify import slugify
import genanki
import requests
import yaml

# Stable IDs (generated once, never change to avoid duplicates)
DECK_ID = 1503075733
MODEL_ID = 1455106195

# Use genanki's built-in cloze model
CLOZE_MODEL = genanki.Model(
    MODEL_ID,
    'Poetry Cloze',
    fields=[
        {'name': 'Text'},
        {'name': 'LineNo'},
        {'name': 'Title'},
        {'name': 'Author'},
        {'name': 'Metadata'},
    ],
    templates=[
        {
            'name': 'Cloze',
            'qfmt': '''<div style="font-family: 'EB Garamond', serif; font-size: 18px; line-height: 1.6; text-align: left; max-width: 600px; margin: 0 auto;">
<style>
pre {
    font-family: 'EB Garamond', serif;
    font-size: inherit;
    line-height: inherit;
    white-space: pre;
    margin: 0;
    padding: 0;
    background: none;
    border: none;
}
</style>
{{cloze:Text}}
</div>
<hr>
<div style="font-family: 'EB Garamond', serif; text-align: center; color: #666; font-size: 14px; line-height: 1.4;">
{{Metadata}}
</div>''',
            'afmt': '''<div style="font-family: 'EB Garamond', serif; font-size: 18px; line-height: 1.6; text-align: left; max-width: 600px; margin: 0 auto;">
<style>
pre {
    font-family: 'EB Garamond', serif;
    font-size: inherit;
    line-height: inherit;
    white-space: pre;
    margin: 0;
    padding: 0;
    background: none;
    border: none;
}
</style>
{{cloze:Text}}
</div>
<hr>
<div style="font-family: 'EB Garamond', serif; text-align: center; color: #666; font-size: 14px; line-height: 1.4;">
{{Metadata}}
</div>''',
        },
    ],
    model_type=genanki.Model.CLOZE,
)


def parse_poem_with_metadata(text: str):
    """Parse a poem with YAML frontmatter, returning metadata and poem text."""
    if text.strip().startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1].strip())
                return metadata, parts[2].strip()
            except yaml.YAMLError:
                pass
    
    return {}, text.strip()


def format_metadata_display(metadata, title=None, author=None):
    """Format metadata for display on cards."""
    title = metadata.get('title', title or 'Unknown Title')
    author = metadata.get('author', author or 'Unknown Author')
    collection = metadata.get('collection')
    year = metadata.get('year')
    url = metadata.get('url') or metadata.get('source')
    
    lines = [f'"{title}"', author]
    
    if collection and year:
        lines.append(f'<i>{collection}</i> ({year})')
    elif collection:
        lines.append(f'<i>{collection}</i>')
    elif year:
        lines.append(f'({year})')
    
    if url:
        lines.append(f'<a href="{url}" target="_blank">Source</a>')
    
    return '<br>'.join(lines)


def parse_poem(text: str):
    """Return list[list[str]] → stanzas→lines with preserved whitespace."""
    stanza_texts = [s for s in re.split(r'\n\s*\n', text.strip()) if s.strip()]
    return [[line for line in stanza_text.splitlines() if line.strip()] 
            for stanza_text in stanza_texts]


def cloze_stanza(lines, blank_idx):
    """Create a cloze deletion for the specified line in the stanza with preserved whitespace."""
    safe = lines.copy()
    safe[blank_idx] = f'{{{{c1::{html.escape(safe[blank_idx])}}}}}'
    return '<pre>' + '\n'.join(safe) + '</pre>'


def build_notes(poem_txt, title=None, poet=None, shuffle_stanzas=True):
    """Build Anki notes from a poem text."""
    metadata, poem_content = parse_poem_with_metadata(poem_txt)
    
    title = metadata.get('title', title or 'Unknown Title')
    poet = metadata.get('author', poet or 'Unknown Author')
    metadata_display = format_metadata_display(metadata, title, poet)
    
    stanzas = parse_poem(poem_content)
    notes = []
    
    if shuffle_stanzas:
        max_lines = max(len(stanza) for stanza in stanzas) if stanzas else 0
        
        for pass_num in range(max_lines):
            for stanza_idx, stanza in enumerate(stanzas):
                if stanza:  # Skip empty stanzas
                    line_idx = random.randrange(len(stanza))
                    line_info = f'Stanza {stanza_idx + 1}, Line {line_idx + 1}'
                    
                    note = genanki.Note(
                        model=CLOZE_MODEL,
                        fields=[
                            cloze_stanza(stanza, line_idx),
                            line_info,
                            title,
                            poet,
                            f'{metadata_display}<br>{line_info}'
                        ],
                        tags=[f"title:{slugify(title)}", f"author:{slugify(poet)}", f"pass:{pass_num + 1}"]
                    )
                    notes.append(note)
            
    else:
        for stanza_idx, stanza in enumerate(stanzas):
            for line_idx in range(len(stanza)):
                line_info = f'Stanza {stanza_idx + 1}, Line {line_idx + 1}'
                
                note = genanki.Note(
                    model=CLOZE_MODEL,
                    fields=[
                        cloze_stanza(stanza, line_idx),
                        line_info,
                        title,
                        poet,
                        f'{metadata_display}<br>{line_info}'
                    ],
                    tags=[f"title:{slugify(title)}", f"author:{slugify(poet)}"]
                )
                notes.append(note)
    
    return notes


def send_to_ankiconnect(deck_name, notes):
    """Send notes to a running Anki instance via AnkiConnect."""
    for note in notes:
        if note.model != CLOZE_MODEL:
            print("Warning: Unknown model type for note, skipping...")
            continue
            
        payload = {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": deck_name,
                    "modelName": "Poetry Cloze",
                    "fields": {
                        "Text": note.fields[0],
                        "LineNo": note.fields[1],
                        "Title": note.fields[2],
                        "Author": note.fields[3],
                        "Metadata": note.fields[4],
                    },
                    "tags": note.tags
                }
            }
        }
        
        try:
            response = requests.post("http://localhost:8765", json=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("error"):
                print(f"AnkiConnect error: {result['error']}")
            else:
                print(f"Added line note: {note.fields[2]}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to AnkiConnect: {e}")
            print("Make sure Anki is running with AnkiConnect add-on installed.")
            return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert poetry text files to Anki cloze deletion cards"
    )
    parser.add_argument(
        "-f", "--files", 
        nargs="+", 
        help="Poem markdown files to process (default: all .md files in poems/ directory)"
    )
    parser.add_argument(
        "--mode", 
        choices=["apkg", "ankiconnect"], 
        default="apkg",
        help="Output mode: 'apkg' creates a file, 'ankiconnect' sends to running Anki"
    )
    parser.add_argument(
        "--deck-name",
        default="Poetry",
        help="Name of the parent Anki deck (default: Poetry)"
    )
    parser.add_argument(
        "--output",
        default="poetry.apkg",
        help="Output file name for apkg mode (default: poetry.apkg)"
    )
    parser.add_argument(
        "--shuffle-stanzas",
        action="store_true",
        default=True,
        help="Shuffle which line is blanked in each stanza per review pass (default: True)"
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Disable line shuffling and create one card per line in order"
    )
    parser.add_argument(
        "--individual-decks",
        action="store_true",
        default=True,
        help="Create individual subdecks for each poem (default: True)"
    )
    parser.add_argument(
        "--single-deck",
        action="store_true",
        help="Put all poems in a single deck instead of individual subdecks"
    )
    
    args = parser.parse_args()

    # Handle file input - default to all .md files in poems/ directory if none specified
    if args.files:
        input_files = args.files
    else:
        poems_dir = Path("poems")
        if poems_dir.exists() and poems_dir.is_dir():
            input_files = list(poems_dir.glob("*.md"))
            if not input_files:
                print("No .md files found in poems/ directory")
                return
            input_files = [str(f) for f in input_files]  # Convert Path objects to strings
            print(f"Using all .md files from poems/ directory: {len(input_files)} files found")
        else:
            print("Error: No files specified and poems/ directory not found")
            print("Use -f to specify files or create a poems/ directory with .md files")
            return

    # Handle shuffling flags
    shuffle_stanzas = args.shuffle_stanzas and not args.no_shuffle
    
    # Handle deck organization flags
    use_individual_decks = args.individual_decks and not args.single_deck

    # Dictionary to store deck objects, keyed by deck name
    decks = {}
    total_notes = 0
    
    # Process files and collect poem info
    poem_info = []
    for file_path in input_files:
        path = Path(file_path)
        if not path.exists():
            continue
            
        try:
            txt = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        
        # Parse title and author from filename as fallback
        title = path.stem.replace('_', ' ').title()
        poet = "Unknown"
        
        if "::" in title:
            poet, title = map(str.strip, title.split("::", 1))
        
        notes = build_notes(txt, title, poet, shuffle_stanzas)
        
        if notes:
            actual_title = notes[0].fields[2]
            actual_poet = notes[0].fields[3]
            poem_info.append((file_path, actual_title, actual_poet, notes))
    
    # Detect title collisions
    title_counts = {title: sum(1 for _, t, _, _ in poem_info if t == title) 
                   for _, title, _, _ in poem_info}
    
    # Create decks with collision-aware naming
    for file_path, actual_title, actual_poet, notes in poem_info:
        if use_individual_decks:
            deck_name = (f"{args.deck_name}::{actual_title} ({actual_poet})" 
                        if title_counts[actual_title] > 1 
                        else f"{args.deck_name}::{actual_title}")
        else:
            deck_name = args.deck_name
    
        if deck_name not in decks:
            import hashlib
            deck_id = int(hashlib.md5(deck_name.encode('utf-8')).hexdigest()[:8], 16)
            decks[deck_name] = genanki.Deck(deck_id, deck_name)
        
        deck = decks[deck_name]
        for note in notes:
            deck.add_note(note)
        
        total_notes += len(notes)
        print(f"Processed '{actual_title}' by {actual_poet}: {len(notes)} notes → {deck_name}")

    print(f"\nTotal notes created: {total_notes}")
    print(f"Total decks created: {len(decks)}")
    
    # Create a list of all decks for the package
    all_decks = list(decks.values())
    
    if args.mode == "apkg":
        # Create APKG file with all decks
        package = genanki.Package(all_decks)
        package.write_to_file(args.output)
        print(f"Created {args.output} - import this file into Anki")
        if use_individual_decks and len(all_decks) > 1:
            print(f"Each poem is in its own subdeck under '{args.deck_name}'")
            print("You can study individual poems or select the parent deck to study all poems together")
    else:
        # Send to AnkiConnect
        print("Sending notes to Anki via AnkiConnect...")
        all_notes = []
        for deck in all_decks:
            all_notes.extend(deck.notes)
        
        if send_to_ankiconnect(args.deck_name, all_notes):
            print("Successfully sent all notes to Anki!")
        else:
            print("Failed to send notes to Anki.")


if __name__ == "__main__":
    main()
