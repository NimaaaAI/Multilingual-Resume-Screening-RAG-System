from api.app.ingestion.chunker import chunk_text


def test_chunk_text_empty_string():
    assert chunk_text("") == []


def test_chunk_text_shorter_than_chunk_size():
    text = "just a few words here"
    assert chunk_text(text) == [text]


def test_chunk_text_overlap():
    words = " ".join(f"word{i}" for i in range(400))
    chunks = chunk_text(words, chunk_size=150, overlap=30)

    assert len(chunks) == 4
    assert chunks[0].split()[0] == "word0"
    assert chunks[1].split()[0] == "word120"
    assert chunks[-1].split()[-1] == "word399"
