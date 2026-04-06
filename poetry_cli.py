"""CLI and I/O orchestration for poetry-to-anki."""

import argparse
import hashlib
import logging
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import json
import urllib.error
import urllib.request

import genanki

from poetry_core import Config, NoteBuilder, create_cloze_model, normalize_source_hint, parse_metadata
from poetry_errors import AnkiConnectError, ConfigurationError, FileProcessingError


logger = logging.getLogger("poetry_to_anki")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


class AnkiConnector:
    """Handles sending notes to Anki via AnkiConnect."""

    @staticmethod
    def send_notes(deck_name: str, notes: List[genanki.Note]) -> bool:
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
                        "tags": note.tags,
                    }
                },
            }

            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                "http://localhost:8765",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode())
            except urllib.error.URLError as exc:
                raise AnkiConnectError(
                    f"Failed to connect to AnkiConnect: {exc}. Make sure Anki is running with AnkiConnect installed."
                ) from exc
            except (json.JSONDecodeError, ValueError) as exc:
                raise AnkiConnectError(f"Invalid JSON response from AnkiConnect: {exc}") from exc

            if result.get("error"):
                raise AnkiConnectError(f"AnkiConnect error: {result['error']}")

        return True


def get_input_files(files: Optional[List[str]]) -> List[str]:
    if files:
        for file_path in files:
            if not Path(file_path).exists():
                logger.warning(f"File not found: {file_path}")
        return files

    poems_dir = Path("poems")
    if poems_dir.exists() and poems_dir.is_dir():
        input_files = list(poems_dir.glob("*.md"))
        if not input_files:
            raise FileProcessingError("No .md files found in poems/ directory")
        logger.info(f"Using all .md files from poems/ directory: {len(input_files)} files found")
        return [str(f) for f in input_files]

    raise FileProcessingError("No files specified and poems/ directory not found")


def read_poem_file(file_path: str) -> Tuple[str, str, str]:
    path = Path(file_path)
    if not path.exists():
        raise FileProcessingError(f"File not found: {file_path}")

    try:
        txt = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise FileProcessingError(f"Cannot decode file {file_path}: {exc}") from exc
    except Exception as exc:
        raise FileProcessingError(f"Error reading file {file_path}: {exc}") from exc

    title = path.stem.replace("_", " ").title()
    poet = "Unknown"
    if "::" in title:
        poet, title = map(str.strip, title.split("::", 1))

    return txt, title, poet


def create_deck_name(title: str, author: str, title_counts: Counter, config: Config) -> str:
    if not config.individual_decks:
        return config.deck_name
    if title_counts[title] > 1:
        return f"{config.deck_name}::{title} ({author})"
    return f"{config.deck_name}::{title}"


def get_or_create_deck(decks: Dict[str, genanki.Deck], deck_name: str) -> genanki.Deck:
    if deck_name not in decks:
        deck_id = int(hashlib.md5(deck_name.encode("utf-8")).hexdigest()[:8], 16)
        decks[deck_name] = genanki.Deck(deck_id, deck_name)
    return decks[deck_name]


def process_poems(config: Config) -> Tuple[Dict[str, genanki.Deck], int]:
    input_files = get_input_files(config.files)
    model = create_cloze_model()
    note_builder = NoteBuilder(model)

    poem_info: List[Tuple[str, str, str, List[genanki.Note]]] = []
    for file_path in input_files:
        try:
            txt, title, poet = read_poem_file(file_path)
            notes = note_builder.build_notes(
                txt,
                title,
                poet,
                config,
                source_hint=normalize_source_hint(file_path),
            )
            if notes:
                actual_title = notes[0].fields[2]
                actual_poet = notes[0].fields[3]
                poem_info.append((file_path, actual_title, actual_poet, notes))
        except FileProcessingError as exc:
            logger.warning(f"Skipping {file_path}: {exc}")
        except Exception as exc:
            logger.error(f"Unexpected error processing {file_path}: {exc}")

    if not poem_info:
        raise FileProcessingError("No poems were successfully processed.")

    title_counts = Counter(title for _, title, _, _ in poem_info)
    decks: Dict[str, genanki.Deck] = {}
    total_notes = 0
    for _, actual_title, actual_poet, notes in poem_info:
        deck_name = create_deck_name(actual_title, actual_poet, title_counts, config)
        deck = get_or_create_deck(decks, deck_name)
        for note in notes:
            deck.add_note(note)
        total_notes += len(notes)
        logger.info(f"Processed '{actual_title}' by {actual_poet}: {len(notes)} notes -> {deck_name}")

    return decks, total_notes


def output_results(config: Config, decks: Dict[str, genanki.Deck], total_notes: int) -> None:
    all_decks = list(decks.values())
    logger.info(f"Total notes created: {total_notes}")
    logger.info(f"Total decks created: {len(all_decks)}")

    if config.mode == "apkg":
        try:
            package = genanki.Package(all_decks)
            package.write_to_file(config.output)
            logger.info(f"Created {config.output} - import this file into Anki")
            if config.individual_decks and len(all_decks) > 1:
                logger.info(f"Each poem is in its own subdeck under '{config.deck_name}'")
        except Exception as exc:
            raise FileProcessingError(f"Failed to create APKG file: {exc}") from exc
        return

    logger.info("Sending notes to Anki via AnkiConnect...")
    for deck_name, deck in decks.items():
        if not deck.notes:
            continue
        AnkiConnector.send_notes(deck_name, list(deck.notes))
        logger.info(f"Sent {len(deck.notes)} notes -> {deck_name}")
    logger.info("Successfully sent all notes to Anki!")


def create_config_from_args(args: argparse.Namespace) -> Config:
    return Config(
        files=args.files,
        mode=args.mode,
        deck_name=args.deck_name,
        output=args.output,
        shuffle_stanzas=args.shuffle_stanzas,
        individual_decks=args.individual_decks,
        wrap_lines=args.wrap_lines,
        max_line_length=args.max_line_length,
        multi_stanza_cards=args.multi_stanza,
    )


def add_build_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-f",
        "--files",
        nargs="+",
        help="Poem markdown files to process (default: all .md files in poems/ directory)",
    )
    parser.add_argument(
        "--mode",
        choices=["apkg", "ankiconnect"],
        default="apkg",
        help="Output mode: 'apkg' creates a file, 'ankiconnect' sends to running Anki",
    )
    parser.add_argument(
        "--deck-name",
        default="Poetry",
        help="Name of the parent Anki deck (default: Poetry)",
    )
    parser.add_argument(
        "--output",
        default="poetry.apkg",
        help="Output file name for apkg mode (default: poetry.apkg)",
    )
    parser.add_argument(
        "--shuffle-stanzas",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Shuffle which line is blanked in each stanza per review pass (default: True)",
    )
    parser.add_argument(
        "--no-shuffle",
        dest="shuffle_stanzas",
        action="store_false",
        help="Alias for --no-shuffle-stanzas",
    )
    parser.add_argument(
        "--individual-decks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create individual subdecks for each poem (default: True)",
    )
    parser.add_argument(
        "--single-deck",
        dest="individual_decks",
        action="store_false",
        help="Alias for --no-individual-decks",
    )
    parser.add_argument(
        "--wrap-lines",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Wrap long lines for better mobile/desktop display (default: True)",
    )
    parser.add_argument(
        "--no-wrap",
        dest="wrap_lines",
        action="store_false",
        help="Alias for --no-wrap-lines",
    )
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=50,
        help="Maximum line length before wrapping (default: 50 characters)",
    )
    parser.add_argument(
        "--multi-stanza",
        action="store_true",
        help="Generate additional cards with clozes for two successive stanzas",
    )


def add_validate_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-f",
        "--files",
        nargs="+",
        help="Poem markdown files to validate (default: all .md files in poems/ directory)",
    )


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert poetry text files to Anki cloze deletion cards")
    subparsers = parser.add_subparsers(dest="command")
    build_parser = subparsers.add_parser("build", help="Build Anki decks from poems")
    add_build_arguments(build_parser)
    validate_parser = subparsers.add_parser("validate", help="Validate poem files")
    add_validate_arguments(validate_parser)
    return parser


def parse_cli_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    if argv is None:
        import sys

        argv = sys.argv[1:]

    if not argv:
        argv = ["build"]
    elif argv[0].startswith("-") and argv[0] not in {"-h", "--help"}:
        argv = ["build"] + argv

    parser = create_argument_parser()
    return parser.parse_args(argv)


def validate_poems(files: Optional[List[str]]) -> bool:
    try:
        input_files = get_input_files(files)
    except FileProcessingError as exc:
        logger.error(f"File processing error: {exc}")
        return False

    ok = True
    for file_path in input_files:
        try:
            text, _, _ = read_poem_file(file_path)
            parse_metadata(text)
        except FileProcessingError as exc:
            ok = False
            logger.error(f"{file_path}: {exc}")

    if ok:
        logger.info(f"Validated {len(input_files)} poem file(s).")
    return ok


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_cli_args(argv)

    if args.command == "validate":
        return 0 if validate_poems(args.files) else 1

    try:
        config = create_config_from_args(args)
        decks, total_notes = process_poems(config)
        output_results(config, decks, total_notes)
    except ConfigurationError as exc:
        logger.error(f"Configuration error: {exc}")
        return 1
    except (FileProcessingError, AnkiConnectError) as exc:
        logger.error(f"Processing error: {exc}")
        return 1
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        return 1

    return 0
