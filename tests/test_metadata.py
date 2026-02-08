from poetry_to_anki import format_metadata_display


def test_metadata_formatting_with_url():
    metadata = {
        "title": "Test Poem",
        "author": "Test Author",
        "collection": "Test Collection",
        "year": 1999,
        "url": "https://example.com/poem",
    }

    display = format_metadata_display(metadata)
    expected = (
        '"Test Poem"<br>Test Author<br><i>Test Collection</i> (1999)'
        '<br><a href="https://example.com/poem" target="_blank">Source</a>'
    )
    assert display == expected


def test_metadata_escapes_html_fields():
    metadata = {
        "title": "<script>alert(1)</script>",
        "author": "A <b>Writer</b>",
        "collection": '<img src=x onerror=alert("x")>',
    }

    display = format_metadata_display(metadata)
    assert "<script>" not in display
    assert "<b>" not in display
    assert "<img" not in display
    assert "&lt;script&gt;" in display


def test_metadata_omits_unsafe_url():
    metadata = {
        "title": "Poem",
        "author": "Author",
        "url": "javascript:alert(1)",
    }

    display = format_metadata_display(metadata)
    assert "href=" not in display
    assert "Source</a>" not in display
