from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from course_login.course_access import CourseAccessService, Enrollment
from course_login.infrai_sms import InfraiSms


phone = os.environ.get("DEMO_LEARNER_PHONE")
if not phone:
    raise RuntimeError("Set DEMO_LEARNER_PHONE to an E.164 phone number")

enrollment = Enrollment(
    learner_id="learner-42",
    course_id="checkout-math",
    phone=phone,
    deadline=datetime.now(timezone.utc) + timedelta(days=7),
    educator_id="educator-7",
)
access = CourseAccessService(InfraiSms(), {enrollment.learner_id: enrollment})
print({"sent_to": access.send_login_code(enrollment.learner_id)})
code = input("Code from SMS: ").strip()
print(access.verify_course_access(enrollment.learner_id, code))
print(access.educator_report(enrollment.educator_id))
