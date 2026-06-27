from anki_poems.add_poem import create_filename, validate_url, validate_year


def test_create_filename():
    assert create_filename("The Road Not Taken", "Robert Frost") == "the-road-not-taken.md"
    assert create_filename("Sonnet 18", "William Shakespeare") == "william-shakespeare_sonnet-18.md"
    assert create_filename("Poem", "Emily Dickinson") == "emily-dickinson_poem.md"


def test_validate_year():
    assert validate_year("1925") == 1925
    assert validate_year("800") is None
    assert validate_year("3000") is None
    assert validate_year("abc") is None


def test_validate_url():
    assert validate_url("https://www.poetryfoundation.org/poems/12345")
    assert validate_url("http://example.com")
    assert validate_url("www.example.com") is None
    assert validate_url("ftp://example.com") is None
