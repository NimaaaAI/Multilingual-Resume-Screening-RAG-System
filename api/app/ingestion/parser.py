from io import BytesIO

import docx
from langdetect import detect
from pypdf import PdfReader


def parse_txt(raw_bytes: bytes) -> str:
    return raw_bytes.decode("utf-8")


def parse_pdf(raw_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(raw_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_docx(raw_bytes: bytes) -> str:
    document = docx.Document(BytesIO(raw_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def detect_language(text: str) -> str:
    return detect(text)
