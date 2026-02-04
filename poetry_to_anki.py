#!/usr/bin/env python
"""
Poetry to Anki CLI Tool

Converts poems into Anki cloze deletion cards where each note shows a 13-line
window through the poem (including stanza breaks) with one line blanked out.
"""
import argparse
import logging
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import bleach
import genanki
import requests
import yaml
from markdown_it import MarkdownIt
from slugify import slugify


logger = logging.getLogger("poetry_to_anki")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


# Custom exceptions
class PoetryToAnkiError(Exception):
    """Base exception for poetry-to-anki errors."""


class FileProcessingError(PoetryToAnkiError):
    """Error occurred while processing a file."""


class ConfigurationError(PoetryToAnkiError):
    """Error in configuration validation."""


class AnkiConnectError(PoetryToAnkiError):
    """Error communicating with AnkiConnect."""


MODEL_ID = 1455106195

CARD_TEMPLATE = '<div style="text-align: left;">{{cloze:Text}}<hr>{{Metadata}}</div>'
POEM_WRAPPER_OPEN = '<div style="white-space: pre-wrap;">'
POEM_WRAPPER_CLOSE = "</div>"
MARKDOWN = MarkdownIt("commonmark", {"html": False})
ALLOWED_TAGS = ["em", "strong", "code", "a"]
ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]
_RENDER_INLINE = getattr(MARKDOWN, "render_inline", None) or MARKDOWN.renderInline
CLEANER = bleach.Cleaner(
    tags=ALLOWED_TAGS,
    attributes=ALLOWED_ATTRIBUTES,
    protocols=ALLOWED_PROTOCOLS,
    strip=True,
)


def sanitize_html(rendered: str) -> str:
    return CLEANER.clean(rendered)


def render_inline_markdown(text: str) -> str:
    if text == "":
        return ""
    if text.strip() == "":
        return text
    leading_len = len(text) - len(text.lstrip(" \t"))
    leading_ws = text[:leading_len]
    content = text[leading_len:]
    rendered = _RENDER_INLINE(content)
    return leading_ws + sanitize_html(rendered)


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
    max_line_length: int = 50
    multi_stanza_cards: bool = False

    def __post_init__(self) -> None:
        valid_modes = {"apkg", "ankiconnect"}
        if self.mode not in valid_modes:
            raise ConfigurationError(f"Invalid mode: {self.mode}. Must be one of {sorted(valid_modes)}")
        if not self.deck_name.strip():
            raise ConfigurationError("Deck name cannot be empty")
        if self.mode == "apkg" and not self.output.strip():
            raise ConfigurationError("Output filename cannot be empty in apkg mode")
        if self.max_line_length < 10:
            raise ConfigurationError("Maximum line length must be at least 10 characters")


@dataclass
class Stanza:
    """Represents a stanza with its lines and line groupings."""
    lines: List[str]
    line_groups: Dict[int, int]  # Maps visual line index to logical line index


@dataclass
class LineEntry:
    text: str
    logical_key: Optional[Tuple[int, int]]


@dataclass
class GlobalPoem:
    lines: List[LineEntry]
    logical_to_indices: Dict[Tuple[int, int], List[int]]


def create_cloze_model() -> genanki.Model:
    return genanki.Model(
        MODEL_ID,
        "Poetry Cloze",
        fields=[
            {"name": "Text"},
            {"name": "LineNo"},
            {"name": "Title"},
            {"name": "Author"},
            {"name": "Metadata"},
        ],
        templates=[
            {
                "name": "Cloze",
                "qfmt": CARD_TEMPLATE,
                "afmt": CARD_TEMPLATE,
            },
        ],
        model_type=genanki.Model.CLOZE,
    )


def parse_metadata(text: str) -> Tuple[Dict[str, str], str]:
    """Parse a poem with YAML frontmatter, returning metadata and poem text."""
    if text.strip().startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1].strip()) or {}
                if not isinstance(metadata, dict):
                    raise FileProcessingError("YAML frontmatter must be a mapping.")
                title = metadata.get("title")
                if title is None or str(title).strip() == "":
                    raise FileProcessingError("YAML frontmatter must include a non-empty 'title'.")
                return metadata, parts[2].strip()
            except yaml.YAMLError as exc:
                raise FileProcessingError(f"Invalid YAML frontmatter: {exc}") from exc
    return {}, text.strip()


def wrap_long_lines(lines: List[str], max_length: int = 50) -> Tuple[List[str], Dict[int, int]]:
    """
    Wrap long lines by breaking at word boundaries and indenting continuation lines.

    Returns a tuple of (wrapped_lines, line_groups) where line_groups maps wrapped
    line indices to their original logical line indices.
    """
    wrapped_lines: List[str] = []
    line_groups: Dict[int, int] = {}
    logical_idx = 0

    for line in lines:
        if line.strip() == "":
            wrapped_lines.append(line)
            continue

        leading_whitespace = len(line) - len(line.lstrip())
        content = line.strip()

        if len(line) <= max_length:
            line_groups[len(wrapped_lines)] = logical_idx
            wrapped_lines.append(line)
        else:
            words = content.split()
            if not words:
                line_groups[len(wrapped_lines)] = logical_idx
                wrapped_lines.append(line)
            else:
                current_line = " " * leading_whitespace + words[0]
                for word in words[1:]:
                    if len(current_line) + 1 + len(word) <= max_length:
                        current_line += " " + word
                    else:
                        line_groups[len(wrapped_lines)] = logical_idx
                        wrapped_lines.append(current_line)
                        current_line = " " * (leading_whitespace + 4) + word
                line_groups[len(wrapped_lines)] = logical_idx
                wrapped_lines.append(current_line)

        logical_idx += 1

    return wrapped_lines, line_groups


def parse_stanzas(text: str, wrap_lines: bool = True, max_line_length: int = 50) -> List[Stanza]:
    """Parse poem text into stanzas with line wrapping support."""
    stanzas: List[Stanza] = []
    current: List[str] = []

    for line in text.strip("\n").splitlines():
        if line.strip() == "":
            if current:
                stanzas.append(Stanza(current, {}))
                current = []
            continue
        current.append(line)

    if current:
        stanzas.append(Stanza(current, {}))

    parsed: List[Stanza] = []
    for stanza in stanzas:
        lines = stanza.lines
        if wrap_lines:
            wrapped_lines, line_groups = wrap_long_lines(lines, max_line_length)
            parsed.append(Stanza(wrapped_lines, line_groups))
        else:
            line_groups: Dict[int, int] = {}
            logical_idx = 0
            for i, line in enumerate(lines):
                if line.strip() == "":
                    continue
                line_groups[i] = logical_idx
                logical_idx += 1
            parsed.append(Stanza(lines, line_groups))

    return parsed


def format_metadata_display(metadata: Dict[str, str], title: Optional[str] = None,
                           author: Optional[str] = None) -> str:
    """Format metadata for display on cards."""
    title = metadata.get("title", title or "Unknown Title")
    author = metadata.get("author", author or "Unknown Author")
    collection = metadata.get("collection")
    year = metadata.get("year")
    url = metadata.get("url") or metadata.get("source")

    lines = [f'"{title}"', author]

    if collection and year:
        lines.append(f"<i>{collection}</i> ({year})")
    elif collection:
        lines.append(f"<i>{collection}</i>")
    elif year:
        lines.append(f"({year})")

    if url:
        lines.append(f'<a href="{url}" target="_blank">Source</a>')

    return "<br>".join(lines)


def build_global_poem(stanzas: List[Stanza]) -> GlobalPoem:
    lines: List[LineEntry] = []
    logical_to_indices: Dict[Tuple[int, int], List[int]] = {}

    for stanza_idx, stanza in enumerate(stanzas):
        for visual_idx, line in enumerate(stanza.lines):
            logical_idx = stanza.line_groups.get(visual_idx)
            key = (stanza_idx, logical_idx) if logical_idx is not None else None
            rendered = render_inline_markdown(line)
            index = len(lines)
            lines.append(LineEntry(text=rendered, logical_key=key))
            if key is not None:
                logical_to_indices.setdefault(key, []).append(index)

        if stanza_idx < len(stanzas) - 1:
            lines.append(LineEntry(text="", logical_key=None))

    return GlobalPoem(lines=lines, logical_to_indices=logical_to_indices)


def render_windowed_cloze(
    poem: GlobalPoem,
    target_key: Tuple[int, int],
    max_lines: int = 13,
) -> str:
    entries = poem.lines
    total_lines = len(entries)
    if total_lines == 0:
        return POEM_WRAPPER_OPEN + POEM_WRAPPER_CLOSE

    indices = poem.logical_to_indices.get(target_key, [])
    if not indices:
        return POEM_WRAPPER_OPEN + "\n".join(entry.text for entry in entries) + POEM_WRAPPER_CLOSE

    if total_lines <= max_lines:
        start = 0
        end = total_lines
    else:
        min_i = min(indices)
        max_i = max(indices)
        center = (min_i + max_i) // 2
        start = center - (max_lines // 2)
        start = max(0, min(start, total_lines - max_lines))
        if min_i < start:
            start = min_i
        if max_i > start + max_lines - 1:
            start = max_i - (max_lines - 1)
        start = max(0, min(start, total_lines - max_lines))
        end = start + max_lines

    output_lines: List[str] = []
    for idx in range(start, end):
        entry = entries[idx]
        text = entry.text
        if entry.logical_key == target_key:
            text = f"{{{{c1::{text}}}}}"
        output_lines.append(text)

    return POEM_WRAPPER_OPEN + "\n".join(output_lines) + POEM_WRAPPER_CLOSE


def make_guid(kind: str, poem_key: str, *parts: object) -> str:
    """Create a stable Anki note GUID."""
    guid_parts = [kind, poem_key]
    guid_parts.extend(str(part) for part in parts)
    return genanki.guid_for(*guid_parts)


def normalize_source_hint(file_path: str) -> str:
    path = Path(file_path)
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path.resolve())


def compute_poem_key(metadata: Dict[str, str], title: str, poet: str,
                     source_hint: Optional[str] = None) -> str:
    source = metadata.get("url") or metadata.get("source")
    if source:
        return f"{title}::{poet}::{source}"
    if source_hint:
        return f"{title}::{poet}::{source_hint}"
    return f"{title}::{poet}"


class NoteBuilder:
    """Builds Anki notes from poems."""

    def __init__(self, model: genanki.Model) -> None:
        self.model = model

    def build_notes(self, poem_txt: str, title: Optional[str] = None,
                    poet: Optional[str] = None, config: Optional[Config] = None,
                    source_hint: Optional[str] = None) -> List[genanki.Note]:
        if config is None:
            config = Config()

        metadata_dict, poem_content = parse_metadata(poem_txt)
        title = metadata_dict.get("title", title or "Unknown Title")
        poet = metadata_dict.get("author", poet or "Unknown Author")
        metadata_display = format_metadata_display(metadata_dict, title, poet)
        poem_key = compute_poem_key(metadata_dict, title, poet, source_hint)

        stanzas = parse_stanzas(poem_content, config.wrap_lines, config.max_line_length)
        global_poem = build_global_poem(stanzas)
        notes: List[genanki.Note] = []
        if config.shuffle_stanzas:
            notes.extend(self._build_shuffled_notes(
                stanzas, title, poet, metadata_display, poem_key, global_poem
            ))
        else:
            notes.extend(self._build_sequential_notes(
                stanzas, title, poet, metadata_display, poem_key, global_poem
            ))

        if config.multi_stanza_cards and len(stanzas) >= 2:
            notes.extend(self._build_multi_stanza_notes(
                stanzas, title, poet, metadata_display, poem_key, config.shuffle_stanzas, global_poem
            ))
        return notes

    def _build_shuffled_notes(self, stanzas: List[Stanza], title: str, poet: str,
                              metadata_display: str, poem_key: str,
                              global_poem: GlobalPoem) -> List[genanki.Note]:
        notes: List[genanki.Note] = []
        max_logical_lines = 0
        for stanza in stanzas:
            if stanza.line_groups:
                max_logical_lines = max(max_logical_lines, max(stanza.line_groups.values()) + 1)

        for pass_num in range(max_logical_lines):
            for stanza_idx, stanza in enumerate(stanzas):
                if not stanza.line_groups:
                    continue
                logical_lines = sorted(set(stanza.line_groups.values()))
                if pass_num < len(logical_lines):
                    logical_line_idx = random.choice(logical_lines)
                    notes.append(self._create_note(
                        stanza, stanza_idx, logical_line_idx, title, poet, metadata_display,
                        poem_key, global_poem, pass_num + 1
                    ))
        return notes

    def _build_sequential_notes(self, stanzas: List[Stanza], title: str, poet: str,
                                metadata_display: str, poem_key: str,
                                global_poem: GlobalPoem) -> List[genanki.Note]:
        notes: List[genanki.Note] = []
        for stanza_idx, stanza in enumerate(stanzas):
            if not stanza.line_groups:
                continue
            logical_lines = sorted(set(stanza.line_groups.values()))
            for logical_line_idx in logical_lines:
                notes.append(self._create_note(
                    stanza, stanza_idx, logical_line_idx, title, poet, metadata_display,
                    poem_key, global_poem
                ))
        return notes

    def _create_note(self, stanza: Stanza, stanza_idx: int, logical_line_idx: int,
                     title: str, poet: str, metadata_display: str, poem_key: str,
                     global_poem: GlobalPoem,
                     pass_num: Optional[int] = None) -> genanki.Note:
        line_info = f"Stanza {stanza_idx + 1}, Line {logical_line_idx + 1}"
        tags = [f"title:{slugify(title)}", f"author:{slugify(poet)}"]
        if pass_num:
            tags.append(f"pass:{pass_num}")
            guid = make_guid("line-pass", poem_key, stanza_idx, pass_num)
        else:
            guid = make_guid("line", poem_key, stanza_idx, logical_line_idx)

        cloze_text = render_windowed_cloze(global_poem, (stanza_idx, logical_line_idx))

        return genanki.Note(
            model=self.model,
            fields=[
                cloze_text,
                line_info,
                title,
                poet,
                f"{line_info}<br>{metadata_display}",
            ],
            tags=tags,
            guid=guid,
        )

    def _build_multi_stanza_notes(self, stanzas: List[Stanza], title: str, poet: str,
                                  metadata_display: str, poem_key: str, shuffle: bool,
                                  global_poem: GlobalPoem) -> List[genanki.Note]:
        notes: List[genanki.Note] = []

        for i in range(0, len(stanzas) - 1, 2):
            stanza1 = stanzas[i]
            stanza2 = stanzas[i + 1]
            if not (stanza1.line_groups and stanza2.line_groups):
                continue

            stanza1_lines = sorted(set(stanza1.line_groups.values()))
            stanza2_lines = sorted(set(stanza2.line_groups.values()))

            if len(stanza1_lines) >= 3 or len(stanza2_lines) >= 3:
                continue

            if shuffle:
                total_passes = len(stanza1_lines) + len(stanza2_lines)
                options = [(0, line) for line in stanza1_lines] + [(1, line) for line in stanza2_lines]
                for pass_num in range(total_passes):
                    target_stanza, target_line = random.choice(options)
                    notes.append(self._create_multi_stanza_note(
                        stanza1, stanza2, i, i + 1, target_stanza, target_line,
                        title, poet, metadata_display, poem_key, global_poem, pass_num + 1
                    ))
            else:
                for line_idx in stanza1_lines:
                    notes.append(self._create_multi_stanza_note(
                        stanza1, stanza2, i, i + 1, 0, line_idx,
                        title, poet, metadata_display, poem_key, global_poem
                    ))
                for line_idx in stanza2_lines:
                    notes.append(self._create_multi_stanza_note(
                        stanza1, stanza2, i, i + 1, 1, line_idx,
                        title, poet, metadata_display, poem_key, global_poem
                    ))

        return notes

    def _create_multi_stanza_note(self, stanza1: Stanza, stanza2: Stanza,
                                  stanza1_idx: int, stanza2_idx: int,
                                  target_stanza: int, logical_line_idx: int,
                                  title: str, poet: str, metadata_display: str, poem_key: str,
                                  global_poem: GlobalPoem,
                                  pass_num: Optional[int] = None) -> genanki.Note:
        stanza_name = "first" if target_stanza == 0 else "second"
        line_info = (
            f"Stanzas {stanza1_idx + 1}-{stanza2_idx + 1}, Line {logical_line_idx + 1} "
            f"({stanza_name} stanza)"
        )

        tags = [f"title:{slugify(title)}", f"author:{slugify(poet)}", "multi-stanza"]
        if pass_num:
            tags.append(f"pass:{pass_num}")
            guid = make_guid("multi-pass", poem_key, stanza1_idx, stanza2_idx, pass_num)
        else:
            guid = make_guid(
                "multi",
                poem_key,
                stanza1_idx,
                stanza2_idx,
                target_stanza,
                logical_line_idx,
            )

        target_stanza_idx = stanza1_idx if target_stanza == 0 else stanza2_idx
        cloze_text = render_windowed_cloze(global_poem, (target_stanza_idx, logical_line_idx))

        return genanki.Note(
            model=self.model,
            fields=[
                cloze_text,
                line_info,
                title,
                poet,
                f"{line_info}<br>{metadata_display}",
            ],
            tags=tags,
            guid=guid,
        )


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

            try:
                response = requests.post("http://localhost:8765", json=payload)
                response.raise_for_status()
                result = response.json()
            except requests.exceptions.RequestException as exc:
                raise AnkiConnectError(
                    f"Failed to connect to AnkiConnect: {exc}. Make sure Anki is running with AnkiConnect installed."
                ) from exc

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
        import hashlib
        deck_id = int(hashlib.md5(deck_name.encode("utf-8")).hexdigest()[:8], 16)
        decks[deck_name] = genanki.Deck(deck_id, deck_name)
    return decks[deck_name]


def process_poems(config: Config) -> None:
    try:
        input_files = get_input_files(config.files)
    except FileProcessingError as exc:
        logger.error(f"File processing error: {exc}")
        if not config.files:
            logger.info("Use -f to specify files or create a poems/ directory with .md files")
        return

    model = create_cloze_model()
    note_builder = NoteBuilder(model)

    poem_info = []
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
        logger.error("No poems were successfully processed.")
        return

    title_counts = Counter(title for _, title, _, _ in poem_info)
    decks: Dict[str, genanki.Deck] = {}
    total_notes = 0
    for _, actual_title, actual_poet, notes in poem_info:
        deck_name = create_deck_name(actual_title, actual_poet, title_counts, config)
        deck = get_or_create_deck(decks, deck_name)
        for note in notes:
            deck.add_note(note)
        total_notes += len(notes)
        logger.info(f"Processed '{actual_title}' by {actual_poet}: {len(notes)} notes → {deck_name}")

    output_results(config, decks, total_notes)


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
                logger.info(
                    f"Each poem is in its own subdeck under '{config.deck_name}'"
                )
        except Exception as exc:
            raise FileProcessingError(f"Failed to create APKG file: {exc}") from exc
    else:
        logger.info("Sending notes to Anki via AnkiConnect...")
        all_notes: List[genanki.Note] = []
        for deck in all_decks:
            all_notes.extend(deck.notes)
        AnkiConnector.send_notes(config.deck_name, all_notes)
        logger.info("Successfully sent all notes to Anki!")


# Backward compatibility functions for tests
CLOZE_MODEL = create_cloze_model()


def parse_poem_with_metadata(text: str) -> Tuple[Dict[str, str], str]:
    return parse_metadata(text)


def parse_poem(text: str, wrap_lines: bool = True, max_line_length: int = 50) -> Tuple[List[List[str]], List[Dict[int, int]]]:
    stanzas = parse_stanzas(text, wrap_lines, max_line_length)
    return [stanza.lines for stanza in stanzas], [stanza.line_groups for stanza in stanzas]


def build_notes(poem_txt: str, title: Optional[str] = None, poet: Optional[str] = None,
               shuffle_stanzas: bool = True, wrap_lines: bool = True, max_line_length: int = 50) -> List[genanki.Note]:
    note_builder = NoteBuilder(CLOZE_MODEL)
    config = Config(
        shuffle_stanzas=shuffle_stanzas,
        wrap_lines=wrap_lines,
        max_line_length=max_line_length,
        multi_stanza_cards=False,
    )
    return note_builder.build_notes(poem_txt, title, poet, config)


def send_to_ankiconnect(deck_name: str, notes: List[genanki.Note]) -> bool:
    try:
        return AnkiConnector.send_notes(deck_name, notes)
    except AnkiConnectError:
        return False


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
    parser = argparse.ArgumentParser(
        description="Convert poetry text files to Anki cloze deletion cards",
    )

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


def main() -> int:
    args = parse_cli_args()

    if args.command == "validate":
        return 0 if validate_poems(args.files) else 1

    try:
        config = create_config_from_args(args)
        process_poems(config)
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


if __name__ == "__main__":
    import sys
    sys.exit(main())
