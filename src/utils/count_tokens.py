def count_tokens(text: str) -> int:
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    non_ascii = len(text) - ascii_chars
    # 英文/ASCII：4字符≈1 token；非ASCII（中文等）：1字≈1 token
    return (ascii_chars + 3) // 4 + non_ascii