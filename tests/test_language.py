import pytest

from english_coach.language import detect


def test_pure_japanese():
    assert detect("こんにちは世界") == "ja"


def test_pure_english():
    assert detect("hello world") == "en"


def test_mixed_majority_japanese():
    # 11 JP chars (サーバーを + してください) vs 5 EN letters (start)
    assert detect("サーバーを start してください") == "ja"


def test_mixed_majority_english():
    assert detect("please restart the サーバー") == "en"


def test_equal_counts_returns_ja():
    # tie goes to 'ja' (jp_count >= en_count)
    assert detect("あa") == "ja"


def test_numbers_and_symbols_only():
    assert detect("123!?#") is None


def test_empty_string():
    assert detect("") is None


def test_katakana():
    assert detect("コンピューター") == "ja"


def test_kanji():
    assert detect("日本語") == "ja"


def test_technical_english():
    assert detect("uv run python server.py") == "en"
