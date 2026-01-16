from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ai_guardian_remediation.config import settings

Base = declarative_base()

Session = None

if settings.DATABASE_URL:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    Session = sessionmaker(bind=engine)
    # session = Session()
