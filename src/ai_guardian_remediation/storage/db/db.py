import sys
import logging
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ai_guardian_remediation.config import settings

# TODO: Delete later
# --- Setup logging for SQLAlchemy pool ---
logging.basicConfig(
    level=logging.DEBUG,  # prints all SQLAlchemy debug logs
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("sqlalchemy.pool").setLevel(logging.DEBUG)  # pool events

Base = declarative_base()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)
Session = sessionmaker(bind=engine)
# session = Session()


async def migrate_tables(engine: Engine = engine):
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        logging.error(f"Failed to migrate tables: {str(e)}")
        sys.exit(1)
