#!/usr/bin/env python3
"""Fetch a poem from Poetry Foundation and save to poems/ directory."""

import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from poetry_core import slugify


POETRY_FOUNDATION_PREFIX = "https://www.poetryfoundation.org/poems/"
LINE_DIV_STYLE = "text-indent: -1em; padding-left: 1em;"
GENERIC_TITLES = {"poem", "sonnet", "ode", "song"}


class PoetryFoundationParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title: str = ""
        self.author: str = ""
        self.lines: list = []  # str for text line, None for stanza break
        self.copyright_text: str = ""

        self._in_h1 = False
        self._in_h1_p = False
        self._in_poet_link = False
        self._in_poem_body = False
        self._poem_body_depth = 0
        self._in_line_div = False
        self._in_em = False
        self._current_line = ""
        self._after_poem_body = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "h1":
            self._in_h1 = True
            return

        if tag == "p" and self._in_h1:
            self._in_h1_p = True
            return

        if tag == "a" and not self._in_poem_body:
            href = attrs_dict.get("href", "")
            if href.startswith("/poets/"):
                self._in_poet_link = True
            return

        if tag == "em" and self._in_line_div:
            self._current_line += "*"
            self._in_em = True
            return

        if tag == "div":
            cls = attrs_dict.get("class", "")
            style = attrs_dict.get("style", "")

            if "poem-body" in cls:
                self._in_poem_body = True
                self._poem_body_depth = 1
                return

            if self._in_poem_body:
                self._poem_body_depth += 1
                if LINE_DIV_STYLE in style and not self._in_line_div:
                    self._in_line_div = True
                    self._current_line = ""

    def handle_endtag(self, tag):
        if tag == "h1":
            self._in_h1 = False
            self._in_h1_p = False
            return

        if tag == "p" and self._in_h1_p:
            self._in_h1_p = False
            return

        if tag == "a" and self._in_poet_link:
            self._in_poet_link = False
            return

        if tag == "em" and self._in_em:
            self._current_line += "*"
            self._in_em = False
            return

        if tag == "div" and self._in_poem_body:
            self._poem_body_depth -= 1
            if self._poem_body_depth == 0:
                self._in_poem_body = False
                self._after_poem_body = True
            elif self._in_line_div and self._poem_body_depth == 1:
                # just closed a direct child line div
                line = self._current_line
                if line.strip() == "":
                    # stanza break — deduplicate and skip leading breaks
                    if self.lines and self.lines[-1] is not None:
                        self.lines.append(None)
                else:
                    self.lines.append(line)
                self._in_line_div = False
                self._current_line = ""

    def handle_data(self, data):
        if self._in_h1_p and not self.title:
            self.title = data.strip()
            return

        if self._in_poet_link and not self.author:
            self.author = data.strip()
            return

        if self._in_line_div:
            # Strip CR/LF artifact and the single regular space that follows it.
            # Meaningful indentation uses \xa0 (non-breaking spaces), not regular spaces.
            # Convert \xa0 → regular space so the file stays clean and wrapping works.
            text = data.lstrip("\r\n ").replace("\xa0", " ")
            self._current_line += text
            return

        if self._after_poem_body and not self.copyright_text:
            stripped = data.strip()
            if stripped.startswith("Copyright"):
                self.copyright_text = stripped


def fetch_page(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; anki-poems/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        print(f"Error: HTTP {exc.code} fetching {url}")
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Error: Could not fetch {url}: {exc.reason}")
        sys.exit(1)


def extract_year(copyright_text: str) -> Optional[int]:
    if not copyright_text:
        return None
    match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", copyright_text)
    return int(match.group(1)) if match else None


def build_poem_body(lines: list) -> str:
    parts = []
    for line in lines:
        parts.append("" if line is None else line)
    while parts and parts[-1] == "":
        parts.pop()
    return "\n".join(parts)


def create_filename(title: str, author: str) -> str:
    base_name = slugify(title, max_length=50)
    if len(base_name) < 10 or base_name in GENERIC_TITLES:
        author_slug = slugify(author, max_length=20)
        base_name = f"{author_slug}_{base_name}"
    return f"{base_name}.md"


def write_poem_file(title: str, author: str, year: Optional[int], url: str, body: str) -> Path:
    poems_dir = Path("poems")
    poems_dir.mkdir(exist_ok=True)

    filename = create_filename(title, author)
    file_path = poems_dir / filename

    frontmatter = ["---", f'title: "{title}"', f'author: "{author}"']
    if year:
        frontmatter.append(f"year: {year}")
    frontmatter.append(f'url: "{url}"')
    frontmatter.append("---")

    content = "\n".join(frontmatter) + "\n\n" + body + "\n"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].startswith(POETRY_FOUNDATION_PREFIX):
        print("Usage: python fetch_poem.py <url>")
        print(f"       URL must start with {POETRY_FOUNDATION_PREFIX}")
        return 1

    url = sys.argv[1]
    print(f"Fetching: {url}")

    html_text = fetch_page(url)

    parser = PoetryFoundationParser()
    parser.feed(html_text)

    if not parser.title:
        print("Error: Could not find poem title on page.")
        return 1
    if not parser.author:
        print("Error: Could not find author on page.")
        return 1
    if not parser.lines:
        print("Error: Could not find poem text on page.")
        return 1

    year = extract_year(parser.copyright_text)
    body = build_poem_body(parser.lines)
    file_path = write_poem_file(parser.title, parser.author, year, url, body)

    print(f"Saved: {file_path}")
    print(f"Title: {parser.title}")
    print(f"Author: {parser.author}")
    if year:
        print(f"Year: {year}")
    print(f"Lines: {len([l for l in parser.lines if l is not None])}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nUnexpected error: {exc}")
        sys.exit(1)
