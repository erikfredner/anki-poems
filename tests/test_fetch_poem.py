from anki_poems.fetch_poem import PoetryFoundationParser, build_poem_body


def _parse(html):
    parser = PoetryFoundationParser()
    parser.feed(html)
    return parser


LINE_DIV = '<div style="text-indent: -1em; padding-left: 1em;">'


def test_strips_poem_guide_glosses():
    """Hidden display:none gloss spans (Poem Guides) must not corrupt the text.

    Poetry Foundation wraps glossed vocabulary in two spans: a visible
    annotation word and a hidden definition span. The hidden span's text
    (definition, repeated word inside <strong>) must be skipped, and the
    surrounding words must keep their separating spaces.
    """
    html = (
        '<div class="poem-body">'
        f"{LINE_DIV}\n Call the roller of big cigars,<br></div>"
        f"{LINE_DIV}\n The muscular one, and "
        '<span class="annotation" id="annotation-1">bid</span>'
        '<span id="annotation-1-text" style="display:none">'
        "<strong>bid </strong>Command, order, direct</span>"
        " him whip<br></div>"
        f"{LINE_DIV}\n On which she embroidered "
        '<span class="annotation" id="annotation-7">fantails</span>'
        '<span id="annotation-7-text" style="display:none">'
        "<strong>fantails</strong> Birds with a fan-shaped tail</span>"
        " once<br></div>"
        f"{LINE_DIV}\n from the dresser of "
        '<span class="annotation" id="annotation-6">deal</span>'
        '<span id="annotation-6-text" style="display:none">'
        "<strong>deal</strong> Cheap pine or fir wood</span>"
        ",<br></div>"
        "</div>"
    )

    body = build_poem_body(_parse(html).lines)

    assert body == (
        "Call the roller of big cigars,\n"
        "The muscular one, and bid him whip\n"
        "On which she embroidered fantails once\n"
        "from the dresser of deal,"
    )


def test_em_still_renders_as_markdown():
    """Regression: continuation-chunk handling must not break <em> → *…* output."""
    html = (
        '<div class="poem-body">'
        f"{LINE_DIV}\n Bring <em>flowers</em> in newspapers.<br></div>"
        "</div>"
    )

    body = build_poem_body(_parse(html).lines)

    assert body == "Bring *flowers* in newspapers."
