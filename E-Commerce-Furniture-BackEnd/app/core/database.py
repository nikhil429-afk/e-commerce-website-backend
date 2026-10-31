from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import DATABASE_URL

# echo=False: echo=True logs every SQL statement (slow + leaks data into the console).
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = LocalSession()
    try:
        yield db
    except Exception:
        # Any failure inside a request leaves the session clean for the pool.
        db.rollback()
        raise
    finally:
        db.close()
