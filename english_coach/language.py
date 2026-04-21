def detect(text: str) -> str | None:
    """Return 'ja', 'en', or None if undeterminable.

    Counts hiragana/katakana/CJK chars vs ASCII letters and returns the majority.
    None means both counts are zero (e.g., pure symbols/numbers).
    """
    jp_count = 0
    en_count = 0
    for ch in text:
        cp = ord(ch)
        if (
            0x3040 <= cp <= 0x309F  # hiragana
            or 0x30A0 <= cp <= 0x30FF  # katakana
            or 0x4E00 <= cp <= 0x9FFF  # CJK unified ideographs
            or 0x3400 <= cp <= 0x4DBF  # CJK extension A
            or 0x20000 <= cp <= 0x2A6DF  # CJK extension B
        ):
            jp_count += 1
        elif ch.isascii() and ch.isalpha():
            en_count += 1

    if jp_count == 0 and en_count == 0:
        return None
    return "ja" if jp_count >= en_count else "en"
