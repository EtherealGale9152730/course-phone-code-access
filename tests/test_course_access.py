from datetime import datetime, timezone

from course_login.course_access import CourseAccessService, Enrollment


class RecordingSms:
    def __init__(self) -> None:
        self.verified: list[tuple[str, str]] = []

    def request_code(self, phone: str, idempotency_key: str) -> object:
        return {"accepted": True}

    def verify_code(self, phone: str, code: str, idempotency_key: str) -> object:
        self.verified.append((phone, code))
        return {"verified": True}


def test_deadline_blocks_course_without_consuming_code() -> None:
    sms = RecordingSms()
    enrollment = Enrollment(
        learner_id="learner-42",
        course_id="checkout-math",
        phone="+15551234567",
        deadline=datetime(2026, 8, 13, tzinfo=timezone.utc),
        educator_id="educator-7",
    )
    access = CourseAccessService(sms, {enrollment.learner_id: enrollment})

    decision = access.verify_course_access(
        "learner-42", "123456", datetime(2026, 8, 14, tzinfo=timezone.utc)
    )

    assert decision.granted is False
    assert decision.reason == "deadline_passed"
    assert sms.verified == []
    assert access.educator_report("educator-7") == {
        "verified": 0,
        "deadline_passed": 1,
    }


def test_current_enrollment_verifies_phone_and_grants_access() -> None:
    sms = RecordingSms()
    enrollment = Enrollment(
        learner_id="learner-9",
        course_id="catalog-writing",
        phone="+15557654321",
        deadline=datetime(2026, 8, 20, tzinfo=timezone.utc),
        educator_id="educator-7",
    )
    access = CourseAccessService(sms, {enrollment.learner_id: enrollment})

    decision = access.verify_course_access(
        "learner-9", "654321", datetime(2026, 8, 14, tzinfo=timezone.utc)
    )

    assert decision.granted is True
    assert sms.verified == [("+15557654321", "654321")]
