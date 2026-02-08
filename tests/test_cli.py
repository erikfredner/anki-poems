from types import SimpleNamespace

from poetry_cli import main, output_results, validate_poems
from poetry_to_anki import Config


def test_build_returns_nonzero_when_processing_fails(tmp_path):
    missing_file = tmp_path / "missing.md"
    rc = main(["build", "-f", str(missing_file)])
    assert rc == 1


def test_validate_flags_unterminated_frontmatter(tmp_path):
    bad_file = tmp_path / "bad.md"
    bad_file.write_text(
        """---
title: "Broken"
author: "Nobody"

Line 1
Line 2
""",
        encoding="utf-8",
    )

    assert validate_poems([str(bad_file)]) is False


def test_ankiconnect_preserves_subdeck_names(monkeypatch):
    calls = []

    def fake_send_notes(deck_name, notes):
        calls.append((deck_name, len(notes)))
        return True

    monkeypatch.setattr("poetry_cli.AnkiConnector.send_notes", staticmethod(fake_send_notes))

    config = Config(mode="ankiconnect", deck_name="Poetry", individual_decks=True)
    decks = {
        "Poetry::A": SimpleNamespace(notes=[object(), object()]),
        "Poetry::B": SimpleNamespace(notes=[object()]),
    }
    output_results(config, decks, total_notes=3)

    assert calls == [("Poetry::A", 2), ("Poetry::B", 1)]
