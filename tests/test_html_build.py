from lectio_plus.html_build import build_html


def test_build_html() -> None:
    html = build_html("Title", "Body")
    assert html.startswith("<html>")
    assert "<title>Title</title>" in html
    assert "<body>Body</body>" in html
