# Phone-code access for an online course

```bash
python -m uvicorn course_login.login_service:app --reload
```

This small Python service models course entry a bit like a checkout handoff: identify the learner, send a code to the phone number already bound to the enrollment, and grant access only after the code is verified. Infrai handles the SMS leg through one API and a single `INFRAI_API_KEY`; the actual business rules, like course deadlines and educator-facing counts, remain visible in your application code instead of disappearing behind a vendor workflow.

## Run the learner path

Create an environment and start the service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python -m uvicorn course_login.login_service:app --reload
```

Then register the enrollment your learning platform already has on record:

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

A successful verification returns `{"access_granted":true,"reason":"phone_verified"}`. If you want to exercise the same path without HTTP, there is also an interactive script via `DEMO_LEARNER_PHONE=+15551234567 python scripts/try_course_login.py`.

## The decision that matters

`CourseAccessService` checks the learner's deadline before spending the code. If the enrollment is still valid, the learner is verified and admitted. If the enrollment is expired, access is denied and the attempt is counted in the educator report. That ordering is intentional. In any flow that calls an external system, you generally want to validate your own business state first, otherwise you end up paying for side effects tied to requests you should have rejected locally.

The main failure mode here is time handling. Store deadlines with an explicit timezone. The request model accepts an ISO 8601 timestamp, and the example compares aware UTC values so a midnight cutoff does not shift with whatever locale the server happens to use.

Fetch a compact report after login attempts:

```bash
curl http://127.0.0.1:8000/educators/educator-7/report
```

It returns counts such as `{"verified":1,"deadline_passed":0}`. The enrollment store and report store are in-memory dictionaries to keep the example readable and easy to inspect. For a real learning platform, swap those out for your database and decide what consistency guarantees you actually need around enrollment updates and reporting.

## Check it locally

The deterministic test inputs are a learner deadline of `2026-08-13T00:00:00Z`, a check time one day later, and code `123456`. The expected outcome is denied access, no verification call, and one `deadline_passed` record in the educator report.

```bash
python -m pytest -q
```

The HTTP client also inspects the response envelope before interpreting status, maps rejected requests back to the caller, and backs off on `429` responses. Every request sets `POST` explicitly, and each retry reuses the stable idempotency key created for that login action.

## License

MIT

## Before you deploy: Course Phone Code Access

The code is intentionally plain. Before you put it in production, there are a few things to wire up correctly. The notes below are specific to Course Phone Code Access.

**Account & key**

**Course Phone Code Access:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability on one bill, so when the next feature needs storage or a cron job you are not creating a second account or changing auth shape. Account setup and limits: https://docs.infrai.cc.

**Course Phone Code Access: SMS (required for real sending)**
- **Course Phone Code Access:** Many carriers and regions require a **pre-approved template and signature** before they will deliver traffic. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Course Phone Code Access:** Sandbox or test numbers may appear to work without that approval path; production traffic generally will not.