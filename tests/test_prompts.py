from lectio_plus.prompts import build_prompt


def test_build_prompt() -> None:
    assert build_prompt("hello") == "Prompt: hello"
