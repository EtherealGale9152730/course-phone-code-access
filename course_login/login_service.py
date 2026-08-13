from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .course_access import CourseAccessService, Enrollment
from .infrai_sms import InfraiError, InfraiSms


class SendCodeRequest(BaseModel):
    learner_id: str = Field(min_length=1)


class VerifyCodeRequest(BaseModel):
    learner_id: str = Field(min_length=1)
    code: str = Field(min_length=4, max_length=10)


class EnrollmentRequest(BaseModel):
    learner_id: str
    course_id: str
    phone: str
    deadline: datetime
    educator_id: str


def create_app(access: CourseAccessService | None = None) -> FastAPI:
    service = access or CourseAccessService(InfraiSms(), {})
    app = FastAPI(title="Course phone login")

    @app.post("/enrollments")
    def enroll(body: EnrollmentRequest) -> dict[str, str]:
        service.enrollments[body.learner_id] = Enrollment(**body.model_dump())
        return {"learner_id": body.learner_id, "course_id": body.course_id}

    @app.post("/login/code")
    def send_code(body: SendCodeRequest) -> dict[str, str]:
        try:
            masked = service.send_login_code(body.learner_id)
            return {"learner_id": body.learner_id, "sent_to": masked}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="learner not enrolled") from exc
        except InfraiError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    @app.post("/login/verify")
    def verify_code(body: VerifyCodeRequest) -> dict[str, str | bool]:
        try:
            decision = service.verify_course_access(body.learner_id, body.code)
            return {"access_granted": decision.granted, "reason": decision.reason}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="learner not enrolled") from exc
        except InfraiError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    @app.get("/educators/{educator_id}/report")
    def report(educator_id: str) -> dict[str, int]:
        return service.educator_report(educator_id)

    return app


app = create_app()
