import sys
import logging
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ai_guardian_remediation.config import settings

Base = declarative_base()

# TODO: Add the env vars here
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


async def migrate_tables(engine: Engine = engine):
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        logging.error(f"Failed to migrate tables: {str(e)}")
        sys.exit(1)
