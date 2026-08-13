from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4


class SmsVerifier(Protocol):
    def request_code(self, phone: str, idempotency_key: str) -> object:
        return object()

    def verify_code(self, phone: str, code: str, idempotency_key: str) -> object:
        return object()


@dataclass(frozen=True)
class Enrollment:
    learner_id: str
    course_id: str
    phone: str
    deadline: datetime
    educator_id: str


@dataclass(frozen=True)
class AccessDecision:
    granted: bool
    reason: str


class CourseAccessService:
    def __init__(self, sms: SmsVerifier, enrollments: dict[str, Enrollment]) -> None:
        self.sms = sms
        self.enrollments = enrollments
        self.decisions: list[tuple[str, AccessDecision]] = []

    def send_login_code(self, learner_id: str) -> str:
        enrollment = self.enrollments[learner_id]
        self.sms.request_code(enrollment.phone, str(uuid4()))
        return enrollment.phone[-4:].rjust(len(enrollment.phone), "*")

    def verify_course_access(
        self, learner_id: str, code: str, now: datetime | None = None
    ) -> AccessDecision:
        enrollment = self.enrollments[learner_id]
        checked_at = now or datetime.now(timezone.utc)
        if checked_at > enrollment.deadline:
            decision = AccessDecision(False, "deadline_passed")
        else:
            self.sms.verify_code(enrollment.phone, code, str(uuid4()))
            decision = AccessDecision(True, "phone_verified")
        self.decisions.append((learner_id, decision))
        return decision

    def educator_report(self, educator_id: str) -> dict[str, int]:
        learner_ids = {
            item.learner_id
            for item in self.enrollments.values()
            if item.educator_id == educator_id
        }
        relevant = [decision for learner, decision in self.decisions if learner in learner_ids]
        return {
            "verified": sum(decision.granted for decision in relevant),
            "deadline_passed": sum(
                decision.reason == "deadline_passed" for decision in relevant
            ),
        }
