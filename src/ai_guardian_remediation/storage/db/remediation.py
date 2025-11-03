from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
import uuid
import logging
import enum

from sqlalchemy import Column, String, Text, DateTime, Enum

from ai_guardian_remediation.storage.db.db import Base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY


class Status(enum.Enum):
    STARTED = "STARTED"
    FIX_PENDING = "FIX_PENDING"
    FIX_GENERATED = "FIX_GENERATED"
    PR_RAISED = "PR_RAISED"
    COMPLETED = "COMPLETED"


class Remediation(Base):
    __tablename__ = "remediations"

    id = Column(String, primary_key=True)
    vulnerability_id = Column(String)
    status = Column(Enum(Status), nullable=False)
    fix_commit_sha = Column(String)
    fix_branch = Column(String)
    pr_link = Column(String)
    prompt_id = Column(String)
    conversation = Column(ARRAY(Text), default=[])
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    completed_at = Column(DateTime(timezone=True))


class SQLRemediation:
    def __init__(self, db_session: Session = None):
        self.session = db_session

    def create_remediation(
        self,
        id: str,
        vulnerability_id: str,
    ) -> str:
        remediation = Remediation(
            id=id or str(uuid.uuid4()),
            vulnerability_id=vulnerability_id,
            status=Status.STARTED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        try:
            self.session.add(remediation)
            self.session.commit()
            return remediation.id
        except Exception as e:
            self.session.rollback()
            logging.error(f"Failed to create remediation: {str(e)}")
            return None

    def update_remediation(
        self, remediation_id: str, update_data: dict
    ) -> Optional[Remediation]:
        try:
            remediation = self.session.query(Remediation).get(remediation_id)
            if not remediation:
                return None

            for key, value in update_data.items():
                if key == "conversation":
                    if value is None:  # If value is None, clear the array
                        setattr(remediation, key, [])
                    elif isinstance(
                        value, list
                    ):  # if the value is a list (append multiple items)
                        setattr(
                            remediation,
                            key,
                            func.array_cat(getattr(remediation, key), value),
                        )
                    else:  # if the value is a single item (append one item)
                        setattr(
                            remediation,
                            key,
                            func.array_append(getattr(remediation, key), value),
                        )
                else:
                    if hasattr(remediation, key):
                        setattr(remediation, key, value)

            self.session.commit()
            return remediation
        except Exception as e:
            self.session.rollback()
            logging.error(f"Failed to update remediation status: {str(e)}")
            return None

    def get_remediation_by_id(self, remediation_id: str) -> Optional[dict]:
        try:
            remediation = self.session.query(Remediation).get(remediation_id)
            if not remediation:
                return None

            return {
                "id": remediation.id,
                "vulnerability_id": remediation.vulnerability_id,
                "status": remediation.status,
                "fix_commit_sha": remediation.fix_commit_sha,
                "fix_branch": remediation.fix_branch,
                "pr_link": remediation.pr_link,
                "prompt_id": remediation.prompt_id,
                "conversation": remediation.conversation,
                "created_at": remediation.created_at,
                "updated_at": remediation.updated_at,
                "completed_at": remediation.completed_at,
            }
        except Exception as e:
            logging.error(f"Failed to get remediation: {str(e)}")
            return None

    def get_remediations_by_vulnerability_id(self, vulnerability_id: str) -> list[dict]:
        try:
            remediations = (
                self.session.query(Remediation)
                .filter_by(vulnerability_id=vulnerability_id)
                .all()
            )
            if not remediations:
                return []

            return [
                {
                    "id": r.id,
                    "vulnerability_id": r.vulnerability_id,
                    "status": r.status,
                    "fix_commit_sha": r.fix_commit_sha,
                    "fix_branch": r.fix_branch,
                    "pr_link": r.pr_link,
                    "prompt_id": r.prompt_id,
                    "conversation": r.conversation,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "completed_at": r.completed_at,
                }
                for r in remediations
            ]
        except Exception as e:
            logging.error(f"Failed to get remediations: {str(e)}")
            return []
