from api.app.db.models import Candidate, Resume


def test_create_and_read_candidate(db_session):
    candidate = Candidate(name="Ada Lovelace", email="ada@example.com")
    db_session.add(candidate)
    db_session.commit()

    fetched = db_session.query(Candidate).filter_by(email="ada@example.com").first()
    assert fetched is not None
    assert fetched.name == "Ada Lovelace"
    assert fetched.id is not None


def test_resume_linked_to_candidate(db_session):
    candidate = Candidate(name="Grace Hopper", email="grace@example.com")
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        raw_text="Experienced software engineer.",
        file_type="pdf",
        language="en",
    )
    db_session.add(resume)
    db_session.commit()

    fetched = db_session.query(Resume).filter_by(candidate_id=candidate.id).first()
    assert fetched is not None
    assert fetched.file_type == "pdf"
    assert fetched.raw_text == "Experienced software engineer."


def test_update_candidate(db_session):
    candidate = Candidate(name="Alan Turing", email="alan@example.com")
    db_session.add(candidate)
    db_session.commit()

    candidate.phone_number = "555-0100"
    db_session.commit()

    fetched = db_session.query(Candidate).filter_by(email="alan@example.com").first()
    assert fetched.phone_number == "555-0100"
