import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app.db import models  # noqa: F401  imported so its tables register on Base.metadata
from api.app.db.base import Base

load_dotenv()

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture()
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
