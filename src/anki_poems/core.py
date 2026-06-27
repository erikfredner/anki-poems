"""Core parsing/rendering/note-building logic for poetry-to-anki."""

import html
import re
import random
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import bleach
import genanki
import yaml
from markdown_it import MarkdownIt

from .errors import ConfigurationError, FileProcessingError


def slugify(text: str, max_length: Optional[int] = None) -> str:
    """Convert text to a URL/tag-safe slug using only stdlib."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if max_length:
        text = text[:max_length].rstrip("-")
    return text


MODEL_ID = 1455106195

WINDOW_LINES = 13

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
    line_groups: Dict[int, int]  # visual line index -> logical line index


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


def _split_frontmatter(text: str) -> Optional[Tuple[str, str]]:
    lines = text.splitlines()
    first_content = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if first_content is None or lines[first_content].strip() != "---":
        return None
    end_idx = next(
        (i for i in range(first_content + 1, len(lines)) if lines[i].strip() == "---"),
        None,
    )
    if end_idx is None:
        raise FileProcessingError("YAML frontmatter starts with '---' but closing '---' is missing.")
    metadata_text = "\n".join(lines[first_content + 1 : end_idx])
    poem_body = "\n".join(lines[end_idx + 1 :])
    return metadata_text, poem_body


def parse_metadata(text: str) -> Tuple[Dict[str, object], str]:
    """Parse optional YAML frontmatter; return metadata and poem body."""
    split = _split_frontmatter(text)
    if split is None:
        return {}, text.strip()

    metadata_text, poem_body = split
    try:
        metadata = yaml.safe_load(metadata_text.strip()) or {}
    except yaml.YAMLError as exc:
        raise FileProcessingError(f"Invalid YAML frontmatter: {exc}") from exc

    if not isinstance(metadata, dict):
        raise FileProcessingError("YAML frontmatter must be a mapping.")

    title = metadata.get("title")
    if title is None or str(title).strip() == "":
        raise FileProcessingError("YAML frontmatter must include a non-empty 'title'.")

    return metadata, poem_body.strip()


def wrap_long_lines(lines: List[str], max_length: int = 50) -> Tuple[List[str], Dict[int, int]]:
    """
    Wrap long lines at word boundaries with continuation indentation.

    Returns:
      wrapped_lines: visual lines after wrapping
      line_groups: visual line index -> logical line index
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
    """Parse poem text into stanzas with optional line wrapping."""

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
            for idx, line in enumerate(lines):
                if line.strip() == "":
                    continue
                line_groups[idx] = logical_idx
                logical_idx += 1
            parsed.append(Stanza(lines, line_groups))

    return parsed


def _clean_metadata_text(value: object, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if text == "":
        return fallback
    return html.escape(text)


def _clean_metadata_url(value: object) -> Optional[str]:
    if value is None:
        return None

    url_text = str(value).strip()
    if url_text == "":
        return None

    parsed = urlparse(url_text)
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_PROTOCOLS:
        return None
    if scheme in {"http", "https"} and not parsed.netloc:
        return None

    return html.escape(url_text, quote=True)


def format_metadata_display(
    metadata: Dict[str, object],
    title: Optional[str] = None,
    author: Optional[str] = None,
) -> str:
    """Format metadata HTML displayed on cards."""

    safe_title = _clean_metadata_text(metadata.get("title", title or "Unknown Title"), "Unknown Title")
    safe_author = _clean_metadata_text(metadata.get("author", author or "Unknown Author"), "Unknown Author")
    collection = metadata.get("collection")
    year = metadata.get("year")
    safe_collection = _clean_metadata_text(collection, "") if collection is not None else None
    safe_year = _clean_metadata_text(year, "") if year is not None else None
    safe_url = _clean_metadata_url(metadata.get("url") or metadata.get("source"))

    lines = [f'"{safe_title}"', safe_author]

    if safe_collection and safe_year:
        lines.append(f"<i>{safe_collection}</i> ({safe_year})")
    elif safe_collection:
        lines.append(f"<i>{safe_collection}</i>")
    elif safe_year:
        lines.append(f"({safe_year})")

    if safe_url:
        lines.append(f'<a href="{safe_url}" target="_blank">Source</a>')

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


def _compute_window(
    poem: GlobalPoem,
    target_key: Tuple[int, int],
    max_lines: int = WINDOW_LINES,
) -> Tuple[int, int]:
    """Return (start, end) indices of the display window for the given target key."""
    total_lines = len(poem.lines)
    indices = poem.logical_to_indices.get(target_key, [])
    if not indices or total_lines <= max_lines:
        return 0, total_lines
    min_i = min(indices)
    max_i = max(indices)
    center = (min_i + max_i) // 2
    start = center - (max_lines // 2)
    start = max(0, min(start, total_lines - max_lines))
    if min_i < start:
        start = min_i
    if max_i > start + max_lines - 1:
        start = max_i - (max_lines - 1)
    return start, start + max_lines


def render_windowed_cloze(
    poem: GlobalPoem,
    target_key: Tuple[int, int],
    max_lines: int = WINDOW_LINES,
) -> str:
    entries = poem.lines
    if not entries:
        return POEM_WRAPPER_OPEN + POEM_WRAPPER_CLOSE

    indices = poem.logical_to_indices.get(target_key, [])
    if not indices:
        return POEM_WRAPPER_OPEN + "\n".join(entry.text for entry in entries) + POEM_WRAPPER_CLOSE

    start, end = _compute_window(poem, target_key, max_lines)

    output_lines: List[str] = []
    for idx in range(start, end):
        entry = entries[idx]
        text = entry.text
        if entry.logical_key == target_key:
            text = f"{{{{c1::{text}}}}}"
        output_lines.append(text)

    return POEM_WRAPPER_OPEN + "\n".join(output_lines) + POEM_WRAPPER_CLOSE


_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"\b\w+\b")


def _find_words_in_html(html_text: str) -> List[Tuple[str, int, int]]:
    """Return (word, start, end) tuples for words in html_text, skipping tag content."""
    masked = _TAG_RE.sub(lambda m: " " * len(m.group()), html_text)
    return [(m.group(), m.start(), m.end()) for m in _WORD_RE.finditer(masked)]


def render_windowed_cloze_word(
    poem: GlobalPoem,
    target_key: Tuple[int, int],
    word_idx: int,
    max_lines: int = WINDOW_LINES,
) -> str:
    entries = poem.lines
    target_indices = poem.logical_to_indices.get(target_key, [])
    if not entries or not target_indices:
        return POEM_WRAPPER_OPEN + POEM_WRAPPER_CLOSE

    all_words: List[Tuple[int, str, int, int]] = []
    for tidx in target_indices:
        for w, ws, we in _find_words_in_html(entries[tidx].text):
            all_words.append((tidx, w, ws, we))

    start, end = _compute_window(poem, target_key, max_lines)

    cloze_map: Dict[int, Tuple[int, int, str]] = {}
    if 0 <= word_idx < len(all_words):
        tidx, w, ws, we = all_words[word_idx]
        cloze_map[tidx] = (ws, we, w)

    output_lines: List[str] = []
    for idx in range(start, end):
        entry = entries[idx]
        text = entry.text
        if idx in cloze_map:
            ws, we, w = cloze_map[idx]
            text = text[:ws] + f"{{{{c1::{w}}}}}" + text[we:]
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


def compute_poem_key(
    metadata: Dict[str, object],
    title: str,
    poet: str,
    source_hint: Optional[str] = None,
) -> str:
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

    @staticmethod
    def _logical_lines(stanza: Stanza) -> List[int]:
        return sorted(set(stanza.line_groups.values()))

    def build_notes(
        self,
        poem_txt: str,
        title: Optional[str] = None,
        poet: Optional[str] = None,
        config: Optional[Config] = None,
        source_hint: Optional[str] = None,
    ) -> List[genanki.Note]:
        if config is None:
            config = Config()

        metadata_dict, poem_content = parse_metadata(poem_txt)
        title = str(metadata_dict.get("title", title or "Unknown Title"))
        poet = str(metadata_dict.get("author", poet or "Unknown Author"))
        metadata_display = format_metadata_display(metadata_dict, title, poet)
        poem_key = compute_poem_key(metadata_dict, title, poet, source_hint)

        stanzas = parse_stanzas(poem_content, config.wrap_lines, config.max_line_length)
        global_poem = build_global_poem(stanzas)
        notes: List[genanki.Note] = []
        notes.extend(
            self._build_single_line_notes(
                stanzas, title, poet, metadata_display, poem_key, global_poem,
                shuffle=config.shuffle_stanzas,
            )
        )

        if config.multi_stanza_cards and len(stanzas) >= 2:
            notes.extend(
                self._build_multi_stanza_notes(
                    stanzas,
                    title,
                    poet,
                    metadata_display,
                    poem_key,
                    config.shuffle_stanzas,
                    global_poem,
                )
            )
        return notes

    def _build_single_line_notes(
        self,
        stanzas: List[Stanza],
        title: str,
        poet: str,
        metadata_display: str,
        poem_key: str,
        global_poem: GlobalPoem,
        shuffle: bool,
    ) -> List[genanki.Note]:
        notes: List[genanki.Note] = []

        # Ordered list of (global_idx, stanza_idx, ll_idx, word_count) for every
        # logical line, in poem order. global_idx is the line's first visual line.
        lines: List[Tuple[int, int, int, int]] = []
        for stanza_idx, stanza in enumerate(stanzas):
            for ll_idx in self._logical_lines(stanza):
                target_indices = global_poem.logical_to_indices.get((stanza_idx, ll_idx), [])
                if not target_indices:
                    continue
                word_count = sum(
                    len(_find_words_in_html(global_poem.lines[tidx].text))
                    for tidx in target_indices
                )
                lines.append((min(target_indices), stanza_idx, ll_idx, word_count))

        def emit(units: List[Tuple[int, int, int]]) -> None:
            for stanza_idx, ll_idx, word_idx in units:
                notes.append(
                    self._create_word_note(
                        stanza_idx=stanza_idx,
                        logical_line_idx=ll_idx,
                        word_idx=word_idx,
                        title=title,
                        poet=poet,
                        metadata_display=metadata_display,
                        poem_key=poem_key,
                        global_poem=global_poem,
                    )
                )

        if not shuffle:
            for _, stanza_idx, ll_idx, word_count in lines:
                emit([(stanza_idx, ll_idx, word_idx) for word_idx in range(word_count)])
            return notes

        # Partition lines into consecutive ~WINDOW_LINES-tall chunks, then shuffle
        # all word-clozes within each chunk so the initial review order jumps around
        # the window instead of marching line-by-line. Chunks stay in poem order.
        def emit_shuffled(chunk: List[Tuple[int, int, int, int]]) -> None:
            units = [
                (stanza_idx, ll_idx, word_idx)
                for _, stanza_idx, ll_idx, word_count in chunk
                for word_idx in range(word_count)
            ]
            random.shuffle(units)
            emit(units)

        chunk: List[Tuple[int, int, int, int]] = []
        chunk_start = lines[0][0] if lines else 0
        for line in lines:
            global_idx = line[0]
            if chunk and global_idx >= chunk_start + WINDOW_LINES:
                emit_shuffled(chunk)
                chunk = []
                chunk_start = global_idx
            chunk.append(line)
        if chunk:
            emit_shuffled(chunk)

        return notes

    def _create_word_note(
        self,
        stanza_idx: int,
        logical_line_idx: int,
        word_idx: int,
        title: str,
        poet: str,
        metadata_display: str,
        poem_key: str,
        global_poem: GlobalPoem,
    ) -> genanki.Note:
        line_info = f"Stanza {stanza_idx + 1}, Line {logical_line_idx + 1}, Word {word_idx + 1}"
        tags = [f"title:{slugify(title)}", f"author:{slugify(poet)}"]
        guid = make_guid("word", poem_key, stanza_idx, logical_line_idx, word_idx)
        target_key = (stanza_idx, logical_line_idx)
        cloze_text = render_windowed_cloze_word(global_poem, target_key, word_idx)

        start, end = _compute_window(global_poem, target_key)
        total = len(global_poem.lines)
        window_info = f"Lines {start + 1}-{end} of {total}"

        return genanki.Note(
            model=self.model,
            fields=[
                cloze_text,
                line_info,
                title,
                poet,
                f"{line_info}<br>{window_info}<br>{metadata_display}",
            ],
            tags=tags,
            guid=guid,
        )

    def _build_multi_stanza_notes(
        self,
        stanzas: List[Stanza],
        title: str,
        poet: str,
        metadata_display: str,
        poem_key: str,
        shuffle: bool,
        global_poem: GlobalPoem,
    ) -> List[genanki.Note]:
        notes: List[genanki.Note] = []

        for first_idx in range(0, len(stanzas) - 1, 2):
            stanza1 = stanzas[first_idx]
            stanza2 = stanzas[first_idx + 1]
            stanza1_lines = self._logical_lines(stanza1)
            stanza2_lines = self._logical_lines(stanza2)
            if not (stanza1_lines and stanza2_lines):
                continue

            if len(stanza1_lines) >= 3 or len(stanza2_lines) >= 3:
                continue

            options = [(0, line) for line in stanza1_lines] + [(1, line) for line in stanza2_lines]
            if shuffle:
                random.shuffle(options)
                for pass_num, (target_stanza, target_line) in enumerate(options, start=1):
                    notes.append(
                        self._create_multi_stanza_note(
                            stanza1_idx=first_idx,
                            stanza2_idx=first_idx + 1,
                            target_stanza=target_stanza,
                            logical_line_idx=target_line,
                            title=title,
                            poet=poet,
                            metadata_display=metadata_display,
                            poem_key=poem_key,
                            global_poem=global_poem,
                            pass_num=pass_num,
                        )
                    )
            else:
                for target_stanza, target_line in options:
                    notes.append(
                        self._create_multi_stanza_note(
                            stanza1_idx=first_idx,
                            stanza2_idx=first_idx + 1,
                            target_stanza=target_stanza,
                            logical_line_idx=target_line,
                            title=title,
                            poet=poet,
                            metadata_display=metadata_display,
                            poem_key=poem_key,
                            global_poem=global_poem,
                        )
                    )

        return notes

    def _create_multi_stanza_note(
        self,
        stanza1_idx: int,
        stanza2_idx: int,
        target_stanza: int,
        logical_line_idx: int,
        title: str,
        poet: str,
        metadata_display: str,
        poem_key: str,
        global_poem: GlobalPoem,
        pass_num: Optional[int] = None,
    ) -> genanki.Note:
        stanza_name = "first" if target_stanza == 0 else "second"
        line_info = (
            f"Stanzas {stanza1_idx + 1}-{stanza2_idx + 1}, Line {logical_line_idx + 1} "
            f"({stanza_name} stanza)"
        )

        tags = [f"title:{slugify(title)}", f"author:{slugify(poet)}", "multi-stanza"]
        if pass_num:
            tags.append(f"pass:{pass_num}")

        target_stanza_idx = stanza1_idx if target_stanza == 0 else stanza2_idx
        guid = make_guid("multi", poem_key, stanza1_idx, stanza2_idx, target_stanza, logical_line_idx)
        target_key = (target_stanza_idx, logical_line_idx)
        cloze_text = render_windowed_cloze(global_poem, target_key)

        start, end = _compute_window(global_poem, target_key)
        total = len(global_poem.lines)
        window_info = f"Lines {start + 1}-{end} of {total}"

        return genanki.Note(
            model=self.model,
            fields=[
                cloze_text,
                line_info,
                title,
                poet,
                f"{line_info}<br>{window_info}<br>{metadata_display}",
            ],
            tags=tags,
            guid=guid,
        )
