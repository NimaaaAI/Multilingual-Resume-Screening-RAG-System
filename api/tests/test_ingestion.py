from api.app.ingestion.parser import detect_language, parse_txt


def test_parse_txt_decodes_utf8():
    raw = "Experienced software engineer.".encode("utf-8")
    assert parse_txt(raw) == "Experienced software engineer."


def test_detect_language_english():
    text = "I am a software engineer with five years of experience in Python."
    assert detect_language(text) == "en"


def test_detect_language_persian():
    text = "من یک مهندس نرم افزار با پنج سال تجربه در پایتون هستم."
    assert detect_language(text) == "fa"
