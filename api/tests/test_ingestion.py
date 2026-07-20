from io import BytesIO
from pathlib import Path

import docx

from api.app.ingestion.parser import detect_language, parse_docx, parse_pdf, parse_txt

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_txt_decodes_utf8():
    raw = "Experienced software engineer.".encode("utf-8")
    assert parse_txt(raw) == "Experienced software engineer."


def test_parse_docx_extracts_paragraph_text():
    document = docx.Document()
    document.add_paragraph("Experienced software engineer.")
    buf = BytesIO()
    document.save(buf)

    assert parse_docx(buf.getvalue()) == "Experienced software engineer."


def test_parse_pdf_extracts_text():
    raw = (FIXTURES_DIR / "sample_resume.pdf").read_bytes()
    assert "Experienced software engineer." in parse_pdf(raw)


def test_detect_language_english():
    text = "I am a software engineer with five years of experience in Python."
    assert detect_language(text) == "en"


def test_detect_language_persian():
    text = "من یک مهندس نرم افزار با پنج سال تجربه در پایتون هستم."
    assert detect_language(text) == "fa"
