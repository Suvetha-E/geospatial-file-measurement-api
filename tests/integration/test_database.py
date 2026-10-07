from sqlalchemy.orm import Session
from sqlalchemy import text


def test_database_connection(db_session: Session):
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1
