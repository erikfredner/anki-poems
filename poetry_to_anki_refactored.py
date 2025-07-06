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
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


# Stable IDs (generated once, never change to avoid duplicates)
DECK_ID = 1503075733
MODEL_ID = 1455106195

# CSS Styles
CARD_STYLES = """
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
"""

CARD_TEMPLATE_MAIN = """<div style="font-family: 'EB Garamond', serif; font-size: 18px; line-height: 1.6; text-align: left; max-width: 600px; margin: 0 auto;">
{styles}
{{{{cloze:Text}}}}
</div>
<hr>
<div style="font-family: 'EB Garamond', serif; text-align: center; color: #666; font-size: 14px; line-height: 1.4;">
{{{{Metadata}}}}
</div>"""


@dataclass
class Config:
    """Configuration for poetry processing."""
    files: Optional[List[str]] = None
    mode: str = "apkg"
    deck_name: str = "Poetry"
    output: str = "poetry.apkg"
    shuffle_stanzas: bool = True
    individual_decks: bool = True
    wrap_lines: bool = True
    max_line_length: int = 65


@dataclass
class PoemMetadata:
    """Metadata for a poem."""
    title: str
    author: str
    collection: Optional[str] = None
    year: Optional[int] = None
    url: Optional[str] = None


@dataclass
class Stanza:
    """Represents a stanza with its lines and line groupings."""
    lines: List[str]
    line_groups: Dict[int, int]  # Maps visual line index to logical line index


class AnkiModelFactory:
    """Factory for creating Anki models."""
    
    @staticmethod
    def create_cloze_model() -> genanki.Model:
        """Create the Poetry Cloze model."""
        qfmt = CARD_TEMPLATE_MAIN.format(styles=CARD_STYLES)
        afmt = CARD_TEMPLATE_MAIN.format(styles=CARD_STYLES)
        
        return genanki.Model(
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
                    'qfmt': qfmt,
                    'afmt': afmt,
                },
            ],
            model_type=genanki.Model.CLOZE,
        )


class PoemParser:
    """Handles parsing of poem text and metadata."""
    
    @staticmethod
    def parse_metadata(text: str) -> Tuple[Dict, str]:
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
    
    @staticmethod
    def parse_stanzas(text: str, wrap_lines: bool = True, max_line_length: int = 65) -> List[Stanza]:
        """Parse poem text into stanzas with line wrapping support."""
        stanza_texts = [s for s in re.split(r'\n\s*\n', text.strip()) if s.strip()]
        
        stanzas = []
        for stanza_text in stanza_texts:
            lines = [line for line in stanza_text.splitlines() if line.strip()]
            
            if wrap_lines:
                wrapped_lines, line_groups = LineWrapper.wrap_long_lines(lines, max_line_length)
                stanzas.append(Stanza(wrapped_lines, line_groups))
            else:
                # Create identity mapping for unwrapped lines
                line_groups = {i: i for i in range(len(lines))}
                stanzas.append(Stanza(lines, line_groups))
        
        return stanzas


class LineWrapper:
    """Handles line wrapping functionality."""
    
    @staticmethod
    def wrap_long_lines(lines: List[str], max_length: int = 65) -> Tuple[List[str], Dict[int, int]]:
        """Wrap long lines by breaking at word boundaries and indenting continuation lines."""
        wrapped_lines = []
        line_groups = {}  # Maps wrapped line index to original line index
        original_line_idx = 0
        
        for line in lines:
            # Preserve existing indentation
            leading_whitespace = len(line) - len(line.lstrip())
            content = line.strip()
            
            if len(line) <= max_length:
                line_groups[len(wrapped_lines)] = original_line_idx
                wrapped_lines.append(line)
            else:
                # Split into words while preserving spaces
                words = content.split()
                if not words:
                    line_groups[len(wrapped_lines)] = original_line_idx
                    wrapped_lines.append(line)
                else:
                    # Build wrapped lines - all parts belong to the same original line
                    current_line = ' ' * leading_whitespace + words[0]
                    
                    for word in words[1:]:
                        # Check if adding this word would exceed the limit
                        if len(current_line) + 1 + len(word) <= max_length:
                            current_line += ' ' + word
                        else:
                            # Start new line with additional indentation (4 spaces)
                            line_groups[len(wrapped_lines)] = original_line_idx
                            wrapped_lines.append(current_line)
                            current_line = ' ' * (leading_whitespace + 4) + word
                    
                    # Add the final line
                    line_groups[len(wrapped_lines)] = original_line_idx
                    wrapped_lines.append(current_line)
            
            original_line_idx += 1
        
        return wrapped_lines, line_groups


class MetadataFormatter:
    """Handles formatting of metadata for display."""
    
    @staticmethod
    def format_display(metadata: Dict, title: Optional[str] = None, author: Optional[str] = None) -> str:
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


class ClozeGenerator:
    """Generates cloze deletions for poem lines."""
    
    @staticmethod
    def create_cloze_stanza(lines: List[str], logical_line_idx: int, line_groups: Dict[int, int]) -> str:
        """Create a cloze deletion for the specified logical line."""
        safe = lines.copy()
        
        # Find all wrapped line indices that belong to this logical line
        wrapped_indices = [i for i, orig_idx in line_groups.items() if orig_idx == logical_line_idx]
        
        # Apply cloze deletion to all parts of the wrapped line
        for idx in wrapped_indices:
            if idx < len(safe):
                safe[idx] = f'{{{{c1::{html.escape(safe[idx])}}}}}'
        
        return '<pre>' + '\n'.join(safe) + '</pre>'


class NoteBuilder:
    """Builds Anki notes from poems."""
    
    def __init__(self, model: genanki.Model):
        self.model = model
    
    def build_notes(self, poem_txt: str, title: Optional[str] = None, poet: Optional[str] = None, 
                   config: Optional[Config] = None) -> List[genanki.Note]:
        """Build Anki notes from a poem text."""
        if config is None:
            config = Config()
            
        metadata_dict, poem_content = PoemParser.parse_metadata(poem_txt)
        
        title = metadata_dict.get('title', title or 'Unknown Title')
        poet = metadata_dict.get('author', poet or 'Unknown Author')
        metadata_display = MetadataFormatter.format_display(metadata_dict, title, poet)
        
        stanzas = PoemParser.parse_stanzas(poem_content, config.wrap_lines, config.max_line_length)
        
        if config.shuffle_stanzas:
            return self._build_shuffled_notes(stanzas, title, poet, metadata_display)
        else:
            return self._build_sequential_notes(stanzas, title, poet, metadata_display)
    
    def _build_shuffled_notes(self, stanzas: List[Stanza], title: str, poet: str, 
                            metadata_display: str) -> List[genanki.Note]:
        """Build notes with shuffled line selection."""
        notes = []
        
        # Find the maximum number of logical lines in any stanza
        max_logical_lines = 0
        for stanza in stanzas:
            if stanza.line_groups:
                logical_line_count = max(stanza.line_groups.values()) + 1
                max_logical_lines = max(max_logical_lines, logical_line_count)
        
        for pass_num in range(max_logical_lines):
            for stanza_idx, stanza in enumerate(stanzas):
                if stanza.lines and stanza.line_groups:
                    # Get unique logical line indices for this stanza
                    logical_lines = sorted(set(stanza.line_groups.values()))
                    
                    # Only create a note if this pass is within the range of logical lines
                    if pass_num < len(logical_lines):
                        logical_line_idx = random.choice(logical_lines)
                        note = self._create_note(stanza, stanza_idx, logical_line_idx, 
                                               title, poet, metadata_display, pass_num + 1)
                        notes.append(note)
        
        return notes
    
    def _build_sequential_notes(self, stanzas: List[Stanza], title: str, poet: str, 
                              metadata_display: str) -> List[genanki.Note]:
        """Build notes in sequential order."""
        notes = []
        
        for stanza_idx, stanza in enumerate(stanzas):
            if stanza.line_groups:
                # Get unique logical line indices for this stanza
                logical_lines = sorted(set(stanza.line_groups.values()))
                
                for logical_line_idx in logical_lines:
                    note = self._create_note(stanza, stanza_idx, logical_line_idx, 
                                           title, poet, metadata_display)
                    notes.append(note)
        
        return notes
    
    def _create_note(self, stanza: Stanza, stanza_idx: int, logical_line_idx: int,
                    title: str, poet: str, metadata_display: str, 
                    pass_num: Optional[int] = None) -> genanki.Note:
        """Create a single Anki note."""
        line_info = f'Stanza {stanza_idx + 1}, Line {logical_line_idx + 1}'
        
        tags = [f"title:{slugify(title)}", f"author:{slugify(poet)}"]
        if pass_num:
            tags.append(f"pass:{pass_num}")
        
        return genanki.Note(
            model=self.model,
            fields=[
                ClozeGenerator.create_cloze_stanza(stanza.lines, logical_line_idx, stanza.line_groups),
                line_info,
                title,
                poet,
                f'{line_info}<br>{metadata_display}'
            ],
            tags=tags
        )


class AnkiConnector:
    """Handles sending notes to Anki via AnkiConnect."""
    
    @staticmethod
    def send_notes(deck_name: str, notes: List[genanki.Note]) -> bool:
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
                    return False
                else:
                    print(f"Added line note: {note.fields[2]}")
            except requests.exceptions.RequestException as e:
                print(f"Failed to connect to AnkiConnect: {e}")
                print("Make sure Anki is running with AnkiConnect add-on installed.")
                return False
        return True


class FileHandler:
    """Handles file operations and input processing."""
    
    @staticmethod
    def get_input_files(files: Optional[List[str]]) -> List[str]:
        """Get list of input files to process."""
        if files:
            return files
        
        poems_dir = Path("poems")
        if poems_dir.exists() and poems_dir.is_dir():
            input_files = list(poems_dir.glob("*.md"))
            if not input_files:
                raise ValueError("No .md files found in poems/ directory")
            print(f"Using all .md files from poems/ directory: {len(input_files)} files found")
            return [str(f) for f in input_files]
        else:
            raise ValueError("No files specified and poems/ directory not found")
    
    @staticmethod
    def read_poem_file(file_path: str) -> Tuple[str, str, str]:
        """Read a poem file and extract title, author, and content."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            txt = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Cannot decode file {file_path}: {e}")
        
        # Parse title and author from filename as fallback
        title = path.stem.replace('_', ' ').title()
        poet = "Unknown"
        
        if "::" in title:
            poet, title = map(str.strip, title.split("::", 1))
        
        return txt, title, poet


class DeckManager:
    """Manages Anki deck creation and organization."""
    
    def __init__(self, config: Config):
        self.config = config
        self.decks = {}
        
    def create_deck_name(self, title: str, author: str, title_counts: Dict[str, int]) -> str:
        """Create a deck name based on configuration and title collisions."""
        if not self.config.individual_decks:
            return self.config.deck_name
            
        if title_counts[title] > 1:
            return f"{self.config.deck_name}::{title} ({author})"
        else:
            return f"{self.config.deck_name}::{title}"
    
    def get_or_create_deck(self, deck_name: str) -> genanki.Deck:
        """Get existing deck or create a new one."""
        if deck_name not in self.decks:
            import hashlib
            deck_id = int(hashlib.md5(deck_name.encode('utf-8')).hexdigest()[:8], 16)
            self.decks[deck_name] = genanki.Deck(deck_id, deck_name)
        return self.decks[deck_name]
    
    def get_all_decks(self) -> List[genanki.Deck]:
        """Get all created decks."""
        return list(self.decks.values())


class PoetryToAnkiProcessor:
    """Main processor class that orchestrates the conversion."""
    
    def __init__(self, config: Config):
        self.config = config
        self.model = AnkiModelFactory.create_cloze_model()
        self.note_builder = NoteBuilder(self.model)
        self.deck_manager = DeckManager(config)
    
    def process_poems(self) -> None:
        """Process all poems and create Anki decks."""
        try:
            input_files = FileHandler.get_input_files(self.config.files)
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}")
            if not self.config.files:
                print("Use -f to specify files or create a poems/ directory with .md files")
            return
        
        # Process files and collect poem info
        poem_info = []
        for file_path in input_files:
            try:
                txt, title, poet = FileHandler.read_poem_file(file_path)
                notes = self.note_builder.build_notes(txt, title, poet, self.config)
                
                if notes:
                    actual_title = notes[0].fields[2]
                    actual_poet = notes[0].fields[3]
                    poem_info.append((file_path, actual_title, actual_poet, notes))
            except (FileNotFoundError, ValueError) as e:
                print(f"Skipping {file_path}: {e}")
                continue
        
        if not poem_info:
            print("No poems were successfully processed.")
            return
        
        # Detect title collisions
        title_counts = {title: sum(1 for _, t, _, _ in poem_info if t == title) 
                       for _, title, _, _ in poem_info}
        
        # Create decks and add notes
        total_notes = 0
        for file_path, actual_title, actual_poet, notes in poem_info:
            deck_name = self.deck_manager.create_deck_name(actual_title, actual_poet, title_counts)
            deck = self.deck_manager.get_or_create_deck(deck_name)
            
            for note in notes:
                deck.add_note(note)
            
            total_notes += len(notes)
            print(f"Processed '{actual_title}' by {actual_poet}: {len(notes)} notes → {deck_name}")
        
        self._output_results(total_notes)
    
    def _output_results(self, total_notes: int) -> None:
        """Output the final results."""
        all_decks = self.deck_manager.get_all_decks()
        
        print(f"\nTotal notes created: {total_notes}")
        print(f"Total decks created: {len(all_decks)}")
        
        if self.config.mode == "apkg":
            package = genanki.Package(all_decks)
            package.write_to_file(self.config.output)
            print(f"Created {self.config.output} - import this file into Anki")
            if self.config.individual_decks and len(all_decks) > 1:
                print(f"Each poem is in its own subdeck under '{self.config.deck_name}'")
                print("You can study individual poems or select the parent deck to study all poems together")
        else:
            print("Sending notes to Anki via AnkiConnect...")
            all_notes = []
            for deck in all_decks:
                all_notes.extend(deck.notes)
            
            if AnkiConnector.send_notes(self.config.deck_name, all_notes):
                print("Successfully sent all notes to Anki!")
            else:
                print("Failed to send notes to Anki.")


def create_config_from_args(args: argparse.Namespace) -> Config:
    """Create a Config object from command line arguments."""
    return Config(
        files=args.files,
        mode=args.mode,
        deck_name=args.deck_name,
        output=args.output,
        shuffle_stanzas=args.shuffle_stanzas and not args.no_shuffle,
        individual_decks=args.individual_decks and not args.single_deck,
        wrap_lines=args.wrap_lines and not args.no_wrap,
        max_line_length=args.max_line_length
    )


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
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
    parser.add_argument(
        "--wrap-lines",
        action="store_true",
        default=True,
        help="Wrap long lines for better mobile/desktop display (default: True)"
    )
    parser.add_argument(
        "--no-wrap",
        action="store_true",
        help="Disable line wrapping and keep original line lengths"
    )
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=65,
        help="Maximum line length before wrapping (default: 65 characters)"
    )
    return parser


def main():
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    config = create_config_from_args(args)
    
    processor = PoetryToAnkiProcessor(config)
    processor.process_poems()


if __name__ == "__main__":
    main()
