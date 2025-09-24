from sqlalchemy import Column, String, Text, DateTime

from ai_guardian_remediation.storage.db.db import Base
from sqlalchemy.sql import func


class Remediations(Base):
    __tablename__ = "remediations"

    id = Column(String, primary_key=True)
    scan_result_id = Column(String)
    status = Column(String)
    fix_commit_sha = Column(String)
    pr_link = Column(String)
    prompt_id = Column(String)
    conversation = Column(Text)
    started_at = Column(DateTime)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)


def insert_remediation(session, remediation_data: dict) -> Remediations:
    new_remediation = Remediations(**remediation_data)
    session.add(new_remediation)
    session.commit()
    session.refresh(new_remediation)
    return new_remediation


def update_remediation(
    session, remediation_id: int, update_data: dict
) -> Remediations | None:
    remediation = session.query(Remediations).get(remediation_id)
    if not remediation:
        return None

    for key, value in update_data.items():
        if hasattr(remediation, key):
            setattr(remediation, key, value)

    remediation.updated_at = func.now()

    session.commit()
    session.refresh(remediation)
    return remediation


def get_remediations_by_scan_result_id(
    session, scan_result_id: str
) -> list[Remediations]:
    return session.query(Remediations).filter_by(scan_result_id=scan_result_id).all()


def get_remediation_by_id(session, remediation_id: str) -> Remediations | None:
    return session.query(Remediations).filter_by(id=remediation_id).first()
