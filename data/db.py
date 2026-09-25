"""
db.py - facilitates SQLALchemy connection to SQLite database.
    (1) Engine: tell SQLAlchemy where the database is and how to communicate
        - make it ONCE, reuse it everywhere in the application
    (2) Open working "session" to operate on the data

IMPORTANT: engine and SessionLocal object are used when SessionLocal is imported elsewhere.
As in, they're built ONCE at import time (and NOT for any SUBSEQUENT imports)
SessionLocal is like a CLASS binded to the engine that returns a "session" object.
- Class ITSELF created once.
- Objects created whenever necessary, for specific actions.

Usage: 
    from data.db import SessionLocal
    ...
    # GENERATE A NEW SESSION OBJECT OF CLASS SESSIONLOCAL()
    with SessionLocal() as session:
        # some operation on the database itself

SQLite:
    - entire database lives on a .db file
    - Python process running query = SQLite library writes directly onto file
    So, "connecting" = pointing SQLAlchemy down a file path

    - sessionmaker gives you factory, craeted per unit of work (i.e. API request)
        - create custom methods to do specific operations (i.e. get last 50 passages)
        - but thinly wraps Session's existing functionality

    - create_all() doesn't have ability to EDIT EXISTING tables 
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from backend.models import Base

DB_PATH = Path(__file__).parent / "moxie.db"

# engine object created to speak to SQLite, at this file path
engine = create_engine("sqlite:///" + str(DB_PATH))
SessionLocal = sessionmaker(bind=engine)


def create_tables():
    """One-off machinery to pull schema into existence."""
    Base.metadata.create_all(engine)


def drop_tables():
    """Wipes every table registered on Base.metadata. No undo - full reset."""
    Base.metadata.drop_all(engine)


if __name__ == "__main__":
    create_tables()