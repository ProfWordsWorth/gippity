from lectio_plus.curator import unique


def test_unique_preserves_order() -> None:
    data = ["a", "b", "a", "c", "b"]
    assert unique(data) == ["a", "b", "c"]
