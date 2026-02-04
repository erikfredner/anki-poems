#!/usr/bin/env python
"""Simple test for poetry_to_anki.py functionality"""

from poetry_to_anki import parse_poem, build_notes, parse_poem_with_metadata, format_metadata_display, CLOZE_MODEL

def test_parse_poem():
    """Test poem parsing with stanzas separated by blank lines."""
    sample_text = """Line 1
Line 2

Line 3
Line 4

Line 5"""
    
    stanzas, line_groups = parse_poem(sample_text, wrap_lines=False)
    assert len(stanzas) == 3, f"Expected 3 stanzas, got {len(stanzas)}"
    assert stanzas[0] == ["Line 1", "Line 2"]
    assert stanzas[1] == ["Line 3", "Line 4"] 
    assert stanzas[2] == ["Line 5"]
    print("✓ Poem parsing test passed")

def test_build_notes():
    """Test note building from poem text."""
    poem_text = """Line 1
Line 2

Line 3
Line 4"""
    
    # Test without shuffling to get deterministic behavior
    notes = build_notes(poem_text, "Test Poem", "Test Author", shuffle_stanzas=False)
    
    # Should have 4 notes total (2 lines per stanza × 2 stanzas)
    assert len(notes) == 4, f"Expected 4 notes, got {len(notes)}"
    
    # Check first note (updated field structure)
    first_note = notes[0]
    assert "{{c1::Line 1}}" in first_note.fields[0]  # Cloze text
    assert first_note.fields[1] == "Stanza 1, Line 1"  # Line number (new format)
    assert first_note.fields[2] == "Test Poem"        # Title
    assert first_note.fields[3] == "Test Author"      # Author
    # Metadata should contain the formatted display with line info
    expected_metadata = 'Stanza 1, Line 1<br>"Test Poem"<br>Test Author'
    actual_metadata = first_note.fields[4]
    assert actual_metadata == expected_metadata, f"Expected '{expected_metadata}', got '{actual_metadata}'"
    
    # Check tags
    assert "title:test-poem" in first_note.tags
    assert "author:test-author" in first_note.tags
    
    print("✓ Note building test passed")

def test_yaml_parsing():
    """Test YAML frontmatter parsing."""
    yaml_poem = '''---
title: "The Test"
author: "Test Poet"
collection: "Test Collection"
year: 2024
---

Line 1
Line 2

Line 3'''
    
    metadata, content = parse_poem_with_metadata(yaml_poem)
    assert metadata['title'] == "The Test"
    assert metadata['author'] == "Test Poet"
    assert metadata['collection'] == "Test Collection"
    assert metadata['year'] == 2024
    assert "Line 1" in content
    print("✓ YAML parsing test passed")

def test_metadata_formatting():
    """Test metadata display formatting."""
    metadata = {
        'title': 'Test Poem',
        'author': 'Test Author',
        'collection': 'Test Collection',
        'year': 1999
    }
    
    display = format_metadata_display(metadata)
    expected = '"Test Poem"<br>Test Author<br><i>Test Collection</i> (1999)'
    assert display == expected, f"Expected '{expected}', got '{display}'"
    
    # Test with URL
    metadata_with_url = {
        'title': 'Test Poem',
        'author': 'Test Author',
        'collection': 'Test Collection',
        'year': 1999,
        'url': 'https://example.com/poem'
    }
    
    display_with_url = format_metadata_display(metadata_with_url)
    expected_with_url = '"Test Poem"<br>Test Author<br><i>Test Collection</i> (1999)<br><a href="https://example.com/poem" target="_blank">Source</a>'
    assert display_with_url == expected_with_url, f"Expected '{expected_with_url}', got '{display_with_url}'"
    
    print("✓ Metadata formatting test passed")

def test_url_only_metadata():
    """Test metadata formatting with only URL."""
    metadata_url_only = {
        'title': 'Simple Poem',
        'author': 'Simple Author',
        'url': 'https://poems.example.com/simple'
    }
    
    display = format_metadata_display(metadata_url_only)
    expected = '"Simple Poem"<br>Simple Author<br><a href="https://poems.example.com/simple" target="_blank">Source</a>'
    assert display == expected, f"Expected '{expected}', got '{display}'"
    
    # Test with 'source' field instead of 'url'
    metadata_source_only = {
        'title': 'Another Poem',
        'author': 'Another Author',
        'source': 'https://manuscripts.example.com/poem'
    }
    
    display_source = format_metadata_display(metadata_source_only)
    expected_source = '"Another Poem"<br>Another Author<br><a href="https://manuscripts.example.com/poem" target="_blank">Source</a>'
    assert display_source == expected_source, f"Expected '{expected_source}', got '{display_source}'"
    
    print("✓ URL-only metadata test passed")

def test_stanza_shuffling():
    """Test that stanza shuffling works and disables transitions."""
    poem_text = """---
title: Test Poem
author: Test Author
---

First stanza line one
First stanza line two

Second stanza line one
Second stanza line two

Third stanza line one
Third stanza line two"""
    
    # Test with shuffling enabled
    notes_shuffled = build_notes(poem_text, shuffle_stanzas=True)
    
    # Should have 6 notes (2 lines × 3 stanzas, no transitions because shuffling is enabled)
    assert len(notes_shuffled) == 6, f"Expected 6 notes, got {len(notes_shuffled)}"
    
    # Check that all notes are cloze notes (no transition notes)
    for note in notes_shuffled:
        assert note.model == CLOZE_MODEL, "All notes should be cloze notes when shuffling is enabled"
    
    # Test with shuffling disabled (control case)
    notes_ordered = build_notes(poem_text, shuffle_stanzas=False)
    
    # Should have 6 notes (one per line, no transitions)
    assert len(notes_ordered) == 6, f"Expected 6 notes without shuffling, got {len(notes_ordered)}"
    
    # Check that all notes are cloze notes
    cloze_count = sum(1 for note in notes_ordered if note.model == CLOZE_MODEL)
    assert cloze_count == 6, f"Expected 6 cloze notes, got {cloze_count}"
    
    print("✓ Stanza shuffling test passed")

def test_shuffling_maintains_stanza_content():
    """Test that shuffling doesn't change the content of stanzas, just their order."""
    import random
    
    poem_text = """---
title: Content Test
author: Test Author
---

Line A1
Line A2

Line B1
Line B2

Line C1
Line C2"""
    
    # Set a fixed seed for reproducible testing
    random.seed(42)
    notes_shuffled = build_notes(poem_text, shuffle_stanzas=True)
    
    # Extract all line content from the shuffled notes
    shuffled_lines = []
    for note in notes_shuffled:
        # Extract the cloze text content
        text_field = note.fields[0]  # The "Text" field with cloze
        # Remove HTML tags and cloze markup to get the actual lines
        import re
        # Remove div wrapper tags and extract content
        lines = re.sub(r'</?div[^>]*>', '', text_field)
        lines = re.sub(r'\{\{c1::([^}]+)\}\}', r'\1', lines)
        lines = lines.split('\n')
        shuffled_lines.extend(lines)

    shuffled_lines = [line for line in shuffled_lines if line.strip()]
    
    # The content should include all original lines (context may add extra repeats)
    expected_lines = [
        'Line A1', 'Line A2', 'Line A1', 'Line A2',
        'Line B1', 'Line B2', 'Line B1', 'Line B2',
        'Line C1', 'Line C2', 'Line C1', 'Line C2'
    ]
    
    from collections import Counter
    expected_counts = Counter(expected_lines)
    actual_counts = Counter(shuffled_lines)
    
    for line, count in expected_counts.items():
        assert actual_counts[line] >= count, \
            f"Expected at least {count} occurrences of '{line}', got {actual_counts[line]}"
    
    print("✓ Shuffling content preservation test passed")

def test_individual_deck_creation():
    """Test that individual decks are created for each poem."""
    import tempfile
    from pathlib import Path
    
    # Create temporary poem files
    poem1_content = """---
title: Test Poem One
author: Test Author One
---

First line of poem one
Second line of poem one"""

    poem2_content = """---
title: Test Poem Two  
author: Test Author Two
---

First line of poem two
Second line of poem two"""

    # Create temporary directory and files
    with tempfile.TemporaryDirectory() as temp_dir:
        poem1_path = Path(temp_dir) / "poem1.md"
        poem2_path = Path(temp_dir) / "poem2.md"
        
        poem1_path.write_text(poem1_content)
        poem2_path.write_text(poem2_content)
        
        # Mock the main function's deck creation logic
        from poetry_to_anki import build_notes
        import hashlib
        
        deck_name_base = "Poetry::Main"
        
        # Process first poem
        notes1 = build_notes(poem1_content)
        title1 = notes1[0].fields[2] if notes1 else "Test Poem One"
        deck_name1 = f"{deck_name_base}::{title1}"
        
        deck_id_hash1 = hashlib.md5(deck_name1.encode('utf-8')).hexdigest()
        deck_id1 = int(deck_id_hash1[:8], 16)
        
        # Process second poem
        notes2 = build_notes(poem2_content)
        title2 = notes2[0].fields[2] if notes2 else "Test Poem Two"
        deck_name2 = f"{deck_name_base}::{title2}"
        
        deck_id_hash2 = hashlib.md5(deck_name2.encode('utf-8')).hexdigest()
        deck_id2 = int(deck_id_hash2[:8], 16)
        
        # Verify deck names are different
        assert deck_name1 != deck_name2, "Deck names should be different for different poems"
        assert deck_name1 == "Poetry::Main::Test Poem One"
        assert deck_name2 == "Poetry::Main::Test Poem Two"
        
        # Verify deck IDs are different
        assert deck_id1 != deck_id2, "Deck IDs should be different for different poems"
        
        print("✓ Individual deck creation test passed")

def test_single_vs_individual_deck_modes():
    """Test the difference between single deck and individual deck modes."""
    poem_content = """---
title: Test Poem
author: Test Author  
---

Line one
Line two

Line three
Line four"""
    
    from poetry_to_anki import build_notes
    import hashlib
    
    # Test individual deck mode
    notes = build_notes(poem_content)
    title = notes[0].fields[2] if notes else "Test Poem"
    
    # Individual deck name
    individual_deck_name = f"Poetry::Main::{title}"
    
    # Single deck name  
    single_deck_name = "Poetry::Main"
    
    # Verify names are different
    assert individual_deck_name != single_deck_name
    assert individual_deck_name == "Poetry::Main::Test Poem"
    assert single_deck_name == "Poetry::Main"
    
    # Verify deck IDs would be different
    deck_id_hash1 = hashlib.md5(individual_deck_name.encode('utf-8')).hexdigest()
    deck_id_hash2 = hashlib.md5(single_deck_name.encode('utf-8')).hexdigest()
    
    deck_id1 = int(deck_id_hash1[:8], 16)
    deck_id2 = int(deck_id_hash2[:8], 16)
    
    assert deck_id1 != deck_id2, "Individual and single deck modes should create different deck IDs"
    
    print("✓ Single vs individual deck modes test passed")

def test_new_shuffling_behavior():
    """Test the new shuffling behavior that randomizes lines within each review pass."""
    poem_text = """Line 1
Line 2
Line 3

Line 4
Line 5"""
    
    # Test with new shuffling behavior (default)
    notes = build_notes(poem_text, "Test Poem", "Test Author", shuffle_stanzas=True)
    
    # Stanza 1: 3 lines, Stanza 2: 2 lines → max_lines = 3
    # Pass 1: 2 notes (both stanzas), Pass 2: 2 notes (both stanzas), Pass 3: 1 note (only stanza 1)
    # So we expect 5 notes total
    assert len(notes) == 5, f"Expected 5 notes (2+2+1), got {len(notes)}"
    
    # Check that we have the right number of notes for each pass
    pass1_notes = [n for n in notes if "pass:1" in n.tags]
    pass2_notes = [n for n in notes if "pass:2" in n.tags]
    pass3_notes = [n for n in notes if "pass:3" in n.tags]
    
    assert len(pass1_notes) == 2, f"Expected 2 notes in pass 1, got {len(pass1_notes)}"
    assert len(pass2_notes) == 2, f"Expected 2 notes in pass 2, got {len(pass2_notes)}"
    assert len(pass3_notes) == 1, f"Expected 1 note in pass 3, got {len(pass3_notes)}"
    
    # Check that stanza numbers are preserved (should be "Stanza 1, Line X" and "Stanza 2, Line Y")
    stanza1_notes = [n for n in notes if n.fields[1].startswith("Stanza 1,")]
    stanza2_notes = [n for n in notes if n.fields[1].startswith("Stanza 2,")]
    
    assert len(stanza1_notes) == 3, f"Expected 3 notes for stanza 1, got {len(stanza1_notes)}"
    assert len(stanza2_notes) == 2, f"Expected 2 notes for stanza 2, got {len(stanza2_notes)}"
    
    # Check that each note contains the full stanza with one line cloze-deleted
    for note in stanza1_notes:
        # Should contain all lines from stanza 1, with one being cloze-deleted
        text = note.fields[0]
        assert "Line 1" in text
        assert "Line 2" in text  
        assert "Line 3" in text
        assert "{{c1::" in text  # Should have exactly one cloze deletion
        assert text.count("{{c1::") == 1
    
    print("✓ New shuffling behavior test passed")

def test_metadata_line_accuracy():
    """Test that metadata accurately reflects which line is cloze-deleted (no shuffling)."""
    poem_text = """---
title: "Test Metadata"
author: "Test Author"
---

First line of stanza one
Second line of stanza one
Third line of stanza one

First line of stanza two
Second line of stanza two"""
    
    # Build notes without shuffling for predictable results
    notes = build_notes(poem_text, shuffle_stanzas=False)
    
    # Expected lines in order
    expected_lines = [
        ("First line of stanza one", "Stanza 1, Line 1"),
        ("Second line of stanza one", "Stanza 1, Line 2"),
        ("Third line of stanza one", "Stanza 1, Line 3"),
        ("First line of stanza two", "Stanza 2, Line 1"),
        ("Second line of stanza two", "Stanza 2, Line 2"),
    ]
    
    assert len(notes) == len(expected_lines), f"Expected {len(expected_lines)} notes, got {len(notes)}"
    
    import re
    for i, note in enumerate(notes):
        text_field = note.fields[0]  # Cloze text
        line_info = note.fields[1]   # Line information
        
        # Extract the cloze-deleted text
        cloze_match = re.search(r'\{\{c1::(.*?)\}\}', text_field)
        assert cloze_match, f"Note {i+1}: No cloze deletion found in: {text_field}"
        
        cloze_deleted_line = cloze_match.group(1)
        expected_line, expected_metadata = expected_lines[i]
        
        assert cloze_deleted_line == expected_line, \
            f"Note {i+1}: Expected '{expected_line}', got '{cloze_deleted_line}'"
        assert line_info == expected_metadata, \
            f"Note {i+1}: Expected metadata '{expected_metadata}', got '{line_info}'"
    
    print("✓ Metadata line accuracy test passed")

def test_metadata_line_accuracy_with_shuffling():
    """Test that metadata accurately reflects which line is cloze-deleted (with shuffling)."""
    poem_text = """---
title: "Test Metadata Shuffled"
author: "Test Author"
---

First line of stanza one
Second line of stanza one
Third line of stanza one

First line of stanza two
Second line of stanza two"""
    
    # Build notes with shuffling enabled (default)
    notes = build_notes(poem_text, shuffle_stanzas=True)
    
    # With shuffling, we should get multiple passes through the poem
    # Stanza 1: 3 lines, Stanza 2: 2 lines → max_lines = 3
    # Pass 1: 2 notes, Pass 2: 2 notes, Pass 3: 1 note = 5 total
    assert len(notes) == 5, f"Expected 5 notes with shuffling, got {len(notes)}"
    
    # Available lines by stanza
    stanza_lines = {
        1: [
            "First line of stanza one",
            "Second line of stanza one", 
            "Third line of stanza one"
        ],
        2: [
            "First line of stanza two",
            "Second line of stanza two"
        ]
    }
    
    import re
    for i, note in enumerate(notes):
        text_field = note.fields[0]  # Cloze text
        line_info = note.fields[1]   # Line information
        
        # Extract the cloze-deleted text
        cloze_match = re.search(r'\{\{c1::(.*?)\}\}', text_field)
        assert cloze_match, f"Note {i+1}: No cloze deletion found in: {text_field}"
        
        cloze_deleted_line = cloze_match.group(1)
        
        # Parse the metadata to get stanza and line numbers
        metadata_match = re.search(r'Stanza (\d+), Line (\d+)', line_info)
        assert metadata_match, f"Note {i+1}: Invalid metadata format: {line_info}"
        
        stanza_num = int(metadata_match.group(1))
        line_num = int(metadata_match.group(2))
        
        # Verify the cloze-deleted line matches the metadata
        assert stanza_num in stanza_lines, f"Note {i+1}: Invalid stanza number {stanza_num}"
        assert 1 <= line_num <= len(stanza_lines[stanza_num]), \
            f"Note {i+1}: Invalid line number {line_num} for stanza {stanza_num}"
        
        expected_line = stanza_lines[stanza_num][line_num - 1]  # Convert to 0-based index
        assert cloze_deleted_line == expected_line, \
            f"Note {i+1}: Metadata says '{line_info}' but cloze shows '{cloze_deleted_line}'"
    
    print("✓ Metadata line accuracy with shuffling test passed")


def test_windowed_cloze_center():
    """Test that long poems are windowed to 13 lines with the cloze centered."""
    poem_text = "\n".join([f"Line {i}" for i in range(1, 16)])
    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=False)

    target_note = next((note for note in notes if note.fields[1] == "Stanza 1, Line 8"), None)
    assert target_note is not None, "Expected a note for line 8"

    import re
    content = re.sub(r'</?div[^>]*>', '', target_note.fields[0])
    lines = content.split('\n')

    assert len(lines) == 13, f"Expected 13 lines, got {len(lines)}"
    assert lines[0] == "Line 2", f"Expected window to start at Line 2, got {lines[0]}"
    assert lines[6] == "{{c1::Line 8}}", f"Expected cloze on center line, got {lines[6]}"

    print("✓ Windowed cloze centering test passed")


def test_windowed_cloze_near_end():
    """Test that cloze window shifts when near the end of a poem."""
    poem_text = "\n".join([f"Line {i}" for i in range(1, 21)])
    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=False)

    target_note = next((note for note in notes if note.fields[1] == "Stanza 1, Line 20"), None)
    assert target_note is not None, "Expected a note for line 20"

    import re
    content = re.sub(r'</?div[^>]*>', '', target_note.fields[0])
    lines = content.split('\n')

    assert len(lines) == 13, f"Expected 13 lines, got {len(lines)}"
    assert lines[0] == "Line 8", f"Expected window to start at Line 8, got {lines[0]}"
    assert lines[-1] == "{{c1::Line 20}}", f"Expected cloze on last line, got {lines[-1]}"

    print("✓ Windowed cloze end test passed")


def test_window_counts_wrapped_lines():
    """Test that wrapped lines count toward the 13-line window."""
    long_line = (
        "This is a very long line that should wrap into multiple lines for "
        "testing the window size behavior."
    )
    poem_lines = [f"Line {i}" for i in range(1, 13)]
    poem_text = "\n".join(poem_lines + [long_line])

    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=True, max_line_length=20)
    target_note = next((note for note in notes if note.fields[1] == "Stanza 1, Line 13"), None)
    assert target_note is not None, "Expected a note for stanza 1 line 13"

    import re
    content = re.sub(r'</?div[^>]*>', '', target_note.fields[0])
    lines = content.split('\n')

    assert len(lines) == 13, f"Expected 13 lines, got {len(lines)}"

    from poetry_to_anki import wrap_long_lines
    wrapped, line_groups = wrap_long_lines(poem_lines + [long_line], max_length=20)
    wrap_count = sum(1 for logical in line_groups.values() if logical == 12)
    assert wrap_count >= 2, "Expected the long line to wrap into multiple lines for this test"

    expected_first_line = f"Line {wrap_count}"
    assert lines[0] == expected_first_line, \
        f"Expected window to start at {expected_first_line}, got {lines[0]}"
    cloze_count = content.count("{{c1::")
    assert cloze_count == wrap_count, \
        f"Expected {wrap_count} cloze segments for the wrapped line, got {cloze_count}"

    print("✓ Wrapped line window counting test passed")


def test_window_counts_stanza_break():
    """Test that stanza breaks count as a line in the 13-line window."""
    stanza1 = "\n".join([f"Line {i}" for i in range(1, 8)])
    stanza2 = "\n".join([f"Line {i}" for i in range(8, 15)])
    poem_text = f"{stanza1}\n\n{stanza2}"

    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=False)
    target_note = next((note for note in notes if note.fields[1] == "Stanza 1, Line 7"), None)
    assert target_note is not None, "Expected a note for stanza 1 line 7"

    import re
    content = re.sub(r'</?div[^>]*>', '', target_note.fields[0])
    lines = content.split('\n')

    assert len(lines) == 13, f"Expected 13 lines, got {len(lines)}"
    assert "" in lines, "Expected a blank line for the stanza break"

    print("✓ Stanza break counting test passed")

def test_add_new_poem_functions():
    """Test the functions from add_new_poem.py that can be tested without user interaction."""
    # Import the functions we want to test
    from add_new_poem import create_filename, validate_year, validate_url
    
    # Test filename generation
    test_cases = [
        ("The Road Not Taken", "Robert Frost", "the-road-not-taken.md"),
        ("Sonnet 18", "William Shakespeare", "william-shakespeare_sonnet-18.md"),  # Short/generic title
        ("Poem", "Emily Dickinson", "emily-dickinson_poem.md"),  # Very generic title
        ("The Love Song of J. Alfred Prufrock", "T.S. Eliot", "the-love-song-of-j-alfred-prufrock.md"),
        ("Ozymandias", "Percy Bysshe Shelley", "ozymandias.md"),
    ]
    
    for title, author, expected in test_cases:
        result = create_filename(title, author)
        assert result == expected, f"create_filename('{title}', '{author}') = '{result}', expected '{expected}'"
    
    # Test year validation
    year_tests = [
        ("1925", 1925),
        ("2024", 2024),
        ("800", None),    # Too old
        ("3000", None),   # Too new
        ("abc", None),    # Not a number
        ("", None),       # Empty
        ("1500", 1500),   # Valid edge case
        ("2100", 2100),   # Valid edge case
    ]
    
    for year_input, expected in year_tests:
        result = validate_year(year_input)
        assert result == expected, f"validate_year('{year_input}') = {result}, expected {expected}"
    
    # Test URL validation
    url_tests = [
        ("https://www.poetryfoundation.org/poems/12345", "https://www.poetryfoundation.org/poems/12345"),
        ("http://example.com", "http://example.com"),
        ("www.example.com", None),  # No protocol
        ("not-a-url", None),        # Invalid format
        ("", None),                 # Empty
        ("ftp://example.com", None), # Wrong protocol
    ]
    
    for url_input, expected in url_tests:
        result = validate_url(url_input)
        assert result == expected, f"validate_url('{url_input}') = {result}, expected {expected}"
    
    print("✓ Add new poem functions test passed")

def test_whitespace_preservation():
    """Test that whitespace and indentation are preserved in poems."""
    # Test poem with various whitespace patterns
    whitespace_poem = """---
title: "Whitespace Test"
author: "Test Author"
---

Normal line
    Indented line
        Double indented
Normal again

Short line
               Very indented line
Back to normal"""
    
    notes = build_notes(whitespace_poem, shuffle_stanzas=False)
    
    # Should have 1 stanza × 4 lines + 1 stanza × 3 lines = 7 notes
    assert len(notes) == 7, f"Expected 7 notes, got {len(notes)}"
    
    # Check that whitespace is preserved in the cloze text
    for note in notes:
        text_field = note.fields[0]

        # Should be wrapped in div tags with whitespace preservation
        assert text_field.startswith('<div'), f"Text should start with <div>: {text_field}"
        assert text_field.endswith('</div>'), f"Text should end with </div>: {text_field}"

        # Remove div tags to check content
        import re
        content = re.sub(r'</?div[^>]*>', '', text_field)
        
        # Should contain actual whitespace (spaces/tabs), not HTML entities
        if "Indented line" in content:
            # Should have actual spaces before "Indented line"
            lines = content.split('\n')
            # Find line with "Indented line" (might be in cloze or not)
            indented_line = next((line for line in lines if "Indented line" in line), None)
            if indented_line:
                # Remove cloze markup if present
                clean_line = re.sub(r'\{\{c1::([^}]+)\}\}', r'\1', indented_line)
                assert clean_line.startswith('    '), f"Expected 4 spaces before 'Indented line', got: '{clean_line}'"
        
        if "Very indented line" in content:
            lines = content.split('\n')
            # Find line with "Very indented line" (might be in cloze or not)
            very_indented = next((line for line in lines if "Very indented line" in line), None)
            if very_indented:
                # Remove cloze markup if present
                clean_line = re.sub(r'\{\{c1::([^}]+)\}\}', r'\1', very_indented)
                assert clean_line.startswith('               '), f"Expected many spaces before 'Very indented line', got: '{clean_line}'"
    
    print("✓ Whitespace preservation test passed")

def test_line_wrapping():
    """Test long line wrapping functionality."""
    from poetry_to_anki import wrap_long_lines
    
    # Test basic wrapping
    long_lines = [
        "This is a very long line that should be wrapped when it exceeds the maximum length",
        "Short line",
        "  Indented very long line that should also be wrapped but preserve the initial indentation"
    ]
    
    wrapped, line_groups = wrap_long_lines(long_lines, max_length=40)
    
    # Check that long lines are wrapped into multiple lines
    assert len(wrapped) > len(long_lines), "Long lines should be wrapped into multiple lines"
    
    # Check that short lines are preserved
    assert "Short line" in wrapped, "Short lines should be preserved"
    
    # Check that line groups correctly map wrapped lines to original lines
    assert len(line_groups) == len(wrapped), "Line groups should map all wrapped lines"
    
    # Check that the first long line (index 0) has multiple wrapped parts
    first_line_parts = [i for i, orig_idx in line_groups.items() if orig_idx == 0]
    assert len(first_line_parts) > 1, "First long line should be wrapped into multiple parts"
    
    # Check indentation preservation
    indented_lines = [line for line in wrapped if line.startswith("  ")]
    assert len(indented_lines) >= 1, "Indented lines should preserve indentation"
    
    print("✓ Line wrapping test passed")

def test_multi_stanza_cards():
    """Test multi-stanza card generation."""
    from poetry_to_anki import NoteBuilder, create_cloze_model, Config
    
    # Test poem with 4 stanzas
    poem_text = """Line 1a
Line 1b

Line 2a
Line 2b

Line 3a
Line 3b

Line 4a
Line 4b"""
    
    model = create_cloze_model()
    note_builder = NoteBuilder(model)
    
    # Test with multi-stanza cards enabled
    config = Config(
        shuffle_stanzas=False,  # Use sequential for deterministic testing
        multi_stanza_cards=True
    )
    
    notes = note_builder.build_notes(poem_text, "Test Poem", "Test Author", config)
    
    # Should have regular cards (8 total: 2 lines × 4 stanzas) + multi-stanza cards
    # Multi-stanza cards: stanzas 1-2 (4 cards: 2 from stanza1 + 2 from stanza2) + stanzas 3-4 (4 cards) = 8
    # Total: 8 regular + 8 multi-stanza = 16 notes
    assert len(notes) >= 16, f"Expected at least 16 notes with multi-stanza enabled, got {len(notes)}"
    
    # Check that multi-stanza notes exist
    multi_stanza_notes = [note for note in notes if "multi-stanza" in note.tags]
    assert len(multi_stanza_notes) >= 8, f"Expected at least 8 multi-stanza notes, got {len(multi_stanza_notes)}"
    
    # Check that a multi-stanza note contains content from both stanzas
    multi_note = multi_stanza_notes[0]
    multi_text = multi_note.fields[0]  # The cloze text
    
    # Should contain content from both stanzas but only ONE cloze deletion
    cloze_count = multi_text.count('{{c1::')
    assert cloze_count == 1, f"Expected exactly 1 cloze deletion, got {cloze_count}"
    
    # Should contain lines from both stanzas
    assert "Line 1" in multi_text or "Line 2" in multi_text, "Multi-stanza note should contain lines from both stanzas"
    
    # Check line info format (should specify which stanza the cloze is in)
    line_info = multi_note.fields[1]
    assert "Stanzas" in line_info and ("first stanza" in line_info or "second stanza" in line_info), \
        f"Expected multi-stanza line info format with stanza specification, got: {line_info}"
    
    print("✓ Multi-stanza cards test passed")

def test_multi_stanza_skips_long_stanzas():
    """Test that multi-stanza cards are skipped for long stanzas."""
    from poetry_to_anki import NoteBuilder, create_cloze_model, Config

    poem_text = """Line 1a
Line 1b
Line 1c

Line 2a
Line 2b
Line 2c"""

    model = create_cloze_model()
    note_builder = NoteBuilder(model)
    config = Config(
        shuffle_stanzas=False,
        multi_stanza_cards=True
    )

    notes = note_builder.build_notes(poem_text, "Test Poem", "Test Author", config)
    multi_stanza_notes = [note for note in notes if "multi-stanza" in note.tags]
    assert len(multi_stanza_notes) == 0, "Expected no multi-stanza notes for long stanzas"

    print("✓ Multi-stanza long stanza skip test passed")

if __name__ == "__main__":
    test_parse_poem()
    test_build_notes()
    test_yaml_parsing()
    test_metadata_formatting()
    test_url_only_metadata()
    test_stanza_shuffling()
    test_shuffling_maintains_stanza_content()
    test_individual_deck_creation()
    test_single_vs_individual_deck_modes()
    test_new_shuffling_behavior()
    test_metadata_line_accuracy()
    test_metadata_line_accuracy_with_shuffling()
    test_windowed_cloze_center()
    test_windowed_cloze_near_end()
    test_window_counts_wrapped_lines()
    test_window_counts_stanza_break()
    test_add_new_poem_functions()
    test_whitespace_preservation()
    test_line_wrapping()
    test_multi_stanza_cards()
    test_multi_stanza_skips_long_stanzas()
    print("\n✅ All tests passed!")
