#!/usr/bin/env python
"""
Poetry to Anki CLI Tool

Converts plain-text poems into Anki cloze deletion cards where each stanza 
becomes multiple notes (one blanked-out line per note) with full-stanza answers.
"""
import argparse
import html
import re
from pathlib import Path
from slugify import slugify
import genanki
import requests

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
    ],
    templates=[
        {
            'name': 'Cloze',
            'qfmt': '''<div style="font-family: serif; font-size: 18px; line-height: 1.6; text-align: center;">
{{cloze:Text}}
</div>
<hr>
<div style="text-align: center; color: #666; font-size: 14px;">
<strong>{{Title}}</strong> by {{Author}}<br>
<small>Stanza {{LineNo}}</small>
</div>''',
            'afmt': '''<div style="font-family: serif; font-size: 18px; line-height: 1.6; text-align: center;">
{{cloze:Text}}
</div>
<hr>
<div style="text-align: center; color: #666; font-size: 14px;">
<strong>{{Title}}</strong> by {{Author}}<br>
<small>Stanza {{LineNo}}</small>
</div>''',
        },
    ],
    model_type=genanki.Model.CLOZE,
)


def parse_poem(text: str):
    """Return list[list[str]] → stanzas→lines."""
    # Split on blank lines (one or more empty lines)
    stanzas = [s.strip() for s in re.split(r'\n\s*\n', text.strip()) if s.strip()]
    return [s.splitlines() for s in stanzas]


def cloze_stanza(lines, blank_idx):
    """Create a cloze deletion for the specified line in the stanza."""
    safe = list(lines)
    safe[blank_idx] = f'{{{{c1::{html.escape(safe[blank_idx])}}}}}'
    # Use <br> tags to preserve line breaks in HTML
    return '<br>'.join(safe)


def build_notes(poem_txt, title, poet):
    """Build Anki notes from a poem text."""
    stanzas = parse_poem(poem_txt)
    notes = []
    
    for s_idx, stanza in enumerate(stanzas, 1):
        for l_idx in range(len(stanza)):
            fields = [
                cloze_stanza(stanza, l_idx),      # Text (cloze with <br> formatting)
                f'{s_idx}.{l_idx+1}',             # LineNo
                title,                            # Title
                poet                              # Author
            ]
            note = genanki.Note(
                model=CLOZE_MODEL,
                fields=fields,
                tags=[f"title:{slugify(title)}", f"author:{slugify(poet)}"]
            )
            notes.append(note)
    return notes


def send_to_ankiconnect(deck_name, notes):
    """Send notes to a running Anki instance via AnkiConnect."""
    for note in notes:
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
                print(f"Added note: {note.fields[2]} - Line {note.fields[1]}")
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
        required=True, 
        help="Poem text files to process"
    )
    parser.add_argument(
        "--mode", 
        choices=["apkg", "ankiconnect"], 
        default="apkg",
        help="Output mode: 'apkg' creates a file, 'ankiconnect' sends to running Anki"
    )
    parser.add_argument(
        "--deck-name",
        default="Poetry::Master",
        help="Name of the Anki deck (default: Poetry::Master)"
    )
    parser.add_argument(
        "--output",
        default="poetry.apkg",
        help="Output file name for apkg mode (default: poetry.apkg)"
    )
    
    args = parser.parse_args()

    deck = genanki.Deck(DECK_ID, args.deck_name)
    total_notes = 0
    
    for file_path in args.files:
        path = Path(file_path)
        if not path.exists():
            print(f"Warning: File {file_path} not found, skipping...")
            continue
            
        try:
            txt = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"Warning: Could not read {file_path} as UTF-8, skipping...")
            continue
        
        # Parse title and author from filename
        title = path.stem.replace('_', ' ').title()
        poet = "Unknown"
        
        # Support "poet::title.txt" naming scheme
        if "::" in title:
            poet, title = map(str.strip, title.split("::", 1))
        
        # Build notes for this poem
        notes = build_notes(txt, title, poet)
        for note in notes:
            deck.add_note(note)
        
        total_notes += len(notes)
        print(f"Processed '{title}' by {poet}: {len(notes)} notes")

    print(f"\nTotal notes created: {total_notes}")
    
    if args.mode == "apkg":
        # Create APKG file
        package = genanki.Package(deck)
        package.write_to_file(args.output)
        print(f"Created {args.output} - import this file into Anki")
    else:
        # Send to AnkiConnect
        print("Sending notes to Anki via AnkiConnect...")
        if send_to_ankiconnect(args.deck_name, deck.notes):
            print("Successfully sent all notes to Anki!")
        else:
            print("Failed to send notes to Anki.")


if __name__ == "__main__":
    main()
