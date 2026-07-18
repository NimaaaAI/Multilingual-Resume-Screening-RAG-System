from langdetect import detect


def parse_txt(raw_bytes: bytes) -> str:
    return raw_bytes.decode("utf-8")


def detect_language(text: str) -> str:
    return detect(text)
