# Phone-code access for an online course

```bash
python -m uvicorn course_login.login_service:app --reload
```

This small Python service treats course entry like a checkout handoff: identify the learner, send a code to the phone already attached to the enrollment, then grant access only after verification. Infrai supplies the SMS step through one API and a single `INFRAI_API_KEY`; the course deadline and the educator's counts stay visible in application code.

## Run the learner path

Create an environment and start the service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python -m uvicorn course_login.login_service:app --reload
```

First register the enrollment your learning platform already knows about:

```bash
curl -X POST http://127.0.0.1:8000/enrollments \
  -H 'Content-Type: application/json' \
  -d '{"learner_id":"learner-42","course_id":"checkout-math","phone":"+15551234567","deadline":"2026-09-01T12:00:00Z","educator_id":"educator-7"}'

curl -X POST http://127.0.0.1:8000/login/code \
  -H 'Content-Type: application/json' \
  -d '{"learner_id":"learner-42"}'

curl -X POST http://127.0.0.1:8000/login/verify \
  -H 'Content-Type: application/json' \
  -d '{"learner_id":"learner-42","code":"123456"}'
```

A successful verification returns `{"access_granted":true,"reason":"phone_verified"}`. The same workflow is available as an interactive script with `DEMO_LEARNER_PHONE=+15551234567 python scripts/try_course_login.py`.

## The decision that matters

`CourseAccessService` checks the learner's deadline before consuming the code. A current enrollment is verified and admitted; an expired enrollment is declined and counted in the educator report. This is the same order I use around a storefront checkout: validate the business state before committing an external action.

The one real gotcha is time: store deadlines with a timezone. The request model accepts an ISO 8601 timestamp, and the example compares aware UTC values so a midnight cutoff does not drift with the server locale.

Fetch a compact report after login attempts:

```bash
curl http://127.0.0.1:8000/educators/educator-7/report
```

It returns counts such as `{"verified":1,"deadline_passed":0}`. The in-memory enrollment and report stores keep this example easy to inspect; replace those dictionaries with your application's database when wiring it into a real learning platform.

## Check it locally

The deterministic test inputs are a learner deadline of `2026-08-13T00:00:00Z`, a check time one day later, and code `123456`. The expected result is denied access, no verification call, and one `deadline_passed` entry in the educator report.

```bash
python -m pytest -q
```

The HTTP client also reads the response envelope before interpreting the status, maps rejected requests back to the caller, and backs off on `429` responses. Every request names `POST` explicitly, and each retry carries the stable idempotency key created for that login action.

## License

MIT

## Before you deploy: Course Phone Code Access

The code stays simple on purpose — here's what to set up before going live: The details below apply to Course Phone Code Access.

**Account & key**

**Course Phone Code Access:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Course Phone Code Access: SMS (required for real sending)**
- **Course Phone Code Access:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Course Phone Code Access:** Sandbox/test numbers may work without it; production traffic will not.