#!/usr/bin/env python
"""Backward-compatible entrypoint for poetry-to-anki."""

from typing import Dict, List, Optional, Tuple

import genanki

from poetry_cli import (
    AnkiConnector,
    add_build_arguments,
    add_validate_arguments,
    create_argument_parser,
    create_config_from_args,
    create_deck_name,
    get_input_files,
    get_or_create_deck,
    main,
    output_results,
    parse_cli_args,
    process_poems,
    read_poem_file,
    validate_poems,
)
from poetry_core import (
    Config,
    GlobalPoem,
    LineEntry,
    NoteBuilder,
    Stanza,
    build_global_poem,
    compute_poem_key,
    create_cloze_model,
    format_metadata_display,
    make_guid,
    normalize_source_hint,
    parse_metadata,
    parse_stanzas,
    render_inline_markdown,
    render_windowed_cloze,
    sanitize_html,
    wrap_long_lines,
)
from poetry_errors import AnkiConnectError, ConfigurationError, FileProcessingError, PoetryToAnkiError


# Backward compatibility symbols used by tests/integrations.
CLOZE_MODEL = create_cloze_model()


def parse_poem_with_metadata(text: str) -> Tuple[Dict[str, object], str]:
    return parse_metadata(text)


def parse_poem(
    text: str,
    wrap_lines: bool = True,
    max_line_length: int = 50,
) -> Tuple[List[List[str]], List[Dict[int, int]]]:
    stanzas = parse_stanzas(text, wrap_lines, max_line_length)
    return [stanza.lines for stanza in stanzas], [stanza.line_groups for stanza in stanzas]


def build_notes(
    poem_txt: str,
    title: Optional[str] = None,
    poet: Optional[str] = None,
    shuffle_stanzas: bool = True,
    wrap_lines: bool = True,
    max_line_length: int = 50,
) -> List[genanki.Note]:
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


if __name__ == "__main__":
    import sys

    sys.exit(main())
