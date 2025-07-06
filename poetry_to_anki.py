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
import yaml

# Stable IDs (generated once, never change to avoid duplicates)
DECK_ID = 1503075733
MODEL_ID = 1455106195
TRANSITION_MODEL_ID = 1455106196  # New ID for transition cards

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
            'qfmt': '''<div style="font-family: serif; font-size: 18px; line-height: 1.6; text-align: center;">
{{cloze:Text}}
</div>
<hr>
<div style="text-align: center; color: #666; font-size: 14px;">
{{Metadata}}<br>
<small>Stanza {{LineNo}}</small>
</div>''',
            'afmt': '''<div style="font-family: serif; font-size: 18px; line-height: 1.6; text-align: center;">
{{cloze:Text}}
</div>
<hr>
<div style="text-align: center; color: #666; font-size: 14px;">
{{Metadata}}<br>
<small>Stanza {{LineNo}}</small>
</div>''',
        },
    ],
    model_type=genanki.Model.CLOZE,
)

# Transition model for stanza-to-stanza memorization
TRANSITION_MODEL = genanki.Model(
    TRANSITION_MODEL_ID,
    'Poetry Transition',
    fields=[
        {'name': 'PreviousLines'},
        {'name': 'NextLineCloze'},
        {'name': 'StanzaNumbers'},
        {'name': 'Title'},
        {'name': 'Author'},
        {'name': 'Metadata'},
    ],
    templates=[
        {
            'name': 'Transition',
            'qfmt': '''<div style="font-family: serif; font-size: 18px; line-height: 1.6; text-align: center;">
<div style="color: #666; font-style: italic; margin-bottom: 10px;">
{{PreviousLines}}
</div>
<div style="border-top: 2px solid #ddd; padding-top: 10px;">
{{cloze:NextLineCloze}}
</div>
</div>
<hr>
<div style="text-align: center; color: #666; font-size: 14px;">
{{Metadata}}<br>
<small>Transition: Stanza {{StanzaNumbers}}</small>
</div>''',
            'afmt': '''<div style="font-family: serif; font-size: 18px; line-height: 1.6; text-align: center;">
<div style="color: #666; font-style: italic; margin-bottom: 10px;">
{{PreviousLines}}
</div>
<div style="border-top: 2px solid #ddd; padding-top: 10px;">
{{cloze:NextLineCloze}}
</div>
</div>
<hr>
<div style="text-align: center; color: #666; font-size: 14px;">
{{Metadata}}<br>
<small>Transition: Stanza {{StanzaNumbers}}</small>
</div>''',
        },
    ],
    model_type=genanki.Model.CLOZE,
)


def parse_poem_with_metadata(text: str):
    """Parse a poem with YAML frontmatter, returning metadata and poem text."""
    # Check if the file starts with YAML frontmatter
    if text.strip().startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            # Extract YAML frontmatter and poem content
            yaml_content = parts[1].strip()
            poem_content = parts[2].strip()
            
            try:
                metadata = yaml.safe_load(yaml_content)
            except yaml.YAMLError:
                # Fallback to empty metadata if YAML parsing fails
                metadata = {}
            
            return metadata, poem_content
    
    # No YAML frontmatter, return empty metadata and full text
    return {}, text.strip()


def format_metadata_display(metadata, title=None, author=None):
    """Format metadata for display on cards."""
    title = metadata.get('title', title or 'Unknown Title')
    author = metadata.get('author', author or 'Unknown Author')
    collection = metadata.get('collection')
    year = metadata.get('year')
    
    # Base format: "Title" by Author
    display = f'"{title}" by {author}'
    
    # Add collection and year if available
    if collection and year:
        display += f' from <i>{collection}</i> ({year})'
    elif collection:
        display += f' from <i>{collection}</i>'
    elif year:
        display += f' ({year})'
    
    return display


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


def build_notes(poem_txt, title=None, poet=None, include_transitions=True):
    """Build Anki notes from a poem text."""
    # Parse metadata and poem content
    metadata, poem_content = parse_poem_with_metadata(poem_txt)
    
    # Use metadata if available, otherwise fall back to parameters
    title = metadata.get('title', title or 'Unknown Title')
    poet = metadata.get('author', poet or 'Unknown Author')
    
    # Format the metadata display
    metadata_display = format_metadata_display(metadata, title, poet)
    
    stanzas = parse_poem(poem_content)
    notes = []
    
    # Build regular cloze notes (one per line)
    for s_idx, stanza in enumerate(stanzas, 1):
        for l_idx in range(len(stanza)):
            fields = [
                cloze_stanza(stanza, l_idx),      # Text (cloze with <br> formatting)
                f'{s_idx}.{l_idx+1}',             # LineNo
                title,                            # Title
                poet,                             # Author
                metadata_display                  # Metadata (formatted display)
            ]
            note = genanki.Note(
                model=CLOZE_MODEL,
                fields=fields,
                tags=[f"title:{slugify(title)}", f"author:{slugify(poet)}"]
            )
            notes.append(note)
    
    # Build transition notes between stanzas
    if include_transitions and len(stanzas) > 1:  # Only create transition notes if enabled and there are multiple stanzas
        transition_notes = build_transition_notes(stanzas, title, poet, metadata_display)
        notes.extend(transition_notes)
    
    return notes


def build_transition_notes(stanzas, title, poet, metadata_display):
    """Build transition notes between stanzas."""
    transition_notes = []
    
    for i in range(len(stanzas) - 1):
        current_stanza = stanzas[i]
        next_stanza = stanzas[i + 1]
        
        # Get the last 2 lines of current stanza (or all lines if stanza has ≤2 lines)
        if len(current_stanza) <= 2:
            previous_lines = current_stanza
        else:
            previous_lines = current_stanza[-2:]
        
        # Get the first line of next stanza for cloze
        next_first_line = next_stanza[0]
        
        # Format the previous lines with line breaks
        previous_lines_html = '<br>'.join(previous_lines)
        
        # Create cloze for the first line of next stanza
        next_line_cloze = f'{{{{c1::{html.escape(next_first_line)}}}}}'
        
        # Create the transition note
        fields = [
            previous_lines_html,                    # PreviousLines
            next_line_cloze,                       # NextLineCloze  
            f'{i+1} → {i+2}',                      # StanzaNumbers
            title,                                 # Title
            poet,                                  # Author
            metadata_display                       # Metadata
        ]
        
        note = genanki.Note(
            model=TRANSITION_MODEL,
            fields=fields,
            tags=[f"title:{slugify(title)}", f"author:{slugify(poet)}", "transition"]
        )
        transition_notes.append(note)
    
    return transition_notes


def send_to_ankiconnect(deck_name, notes):
    """Send notes to a running Anki instance via AnkiConnect."""
    for note in notes:
        # Determine model name and fields based on note type
        if note.model == CLOZE_MODEL:
            model_name = "Poetry Cloze"
            fields = {
                "Text": note.fields[0],
                "LineNo": note.fields[1],
                "Title": note.fields[2],
                "Author": note.fields[3],
                "Metadata": note.fields[4],
            }
        elif note.model == TRANSITION_MODEL:
            model_name = "Poetry Transition"
            fields = {
                "PreviousLines": note.fields[0],
                "NextLineCloze": note.fields[1],
                "StanzaNumbers": note.fields[2],
                "Title": note.fields[3],
                "Author": note.fields[4],
                "Metadata": note.fields[5],
            }
        else:
            print("Warning: Unknown model type for note, skipping...")
            continue
            
        payload = {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": deck_name,
                    "modelName": model_name,
                    "fields": fields,
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
                title = note.fields[2] if note.model == CLOZE_MODEL else note.fields[3]
                note_type = "line" if note.model == CLOZE_MODEL else "transition"
                print(f"Added {note_type} note: {title}")
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
    parser.add_argument(
        "--include-transitions",
        action="store_true",
        default=True,
        help="Include transition cards between stanzas (default: True)"
    )
    parser.add_argument(
        "--no-transitions",
        action="store_true",
        help="Disable transition cards between stanzas"
    )
    
    args = parser.parse_args()

    # Handle transition flags
    include_transitions = args.include_transitions and not args.no_transitions

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
        
        # Parse title and author from filename as fallback
        title = path.stem.replace('_', ' ').title()
        poet = "Unknown"
        
        # Support "poet::title.txt" naming scheme as fallback
        if "::" in title:
            poet, title = map(str.strip, title.split("::", 1))
        
        # Build notes for this poem (will use YAML metadata if available)
        notes = build_notes(txt, title, poet, include_transitions)
        for note in notes:
            deck.add_note(note)
        
        # Get the actual title and author used (from metadata or fallback)
        if notes:
            actual_title = notes[0].fields[2]  # Title field
            actual_poet = notes[0].fields[3]   # Author field
        else:
            actual_title, actual_poet = title, poet
        
        total_notes += len(notes)
        print(f"Processed '{actual_title}' by {actual_poet}: {len(notes)} notes")

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
