# EduTrack — Micro-Learning Progress & Analytics API

A prototype REST backend for a micro-learning platform. It tracks user enrollment
and lesson completion, auto-completes courses, unlocks achievements, and serves a
student dashboard plus a leaderboard.

Built with **FastAPI**, **SQLAlchemy 2.0** (ORM with foreign keys + relationships),
**SQLite**, and **Pydantic v2** for request/response validation.

## Project layout

```
edutrack/
├── app/
│   ├── main.py            # FastAPI app, router wiring, startup seeding
│   ├── database.py        # Engine, session, Base, get_db dependency
│   ├── models.py          # SQLAlchemy ORM models (Users, Courses, Enrollments, Achievements)
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── crud.py            # Service layer: business rules + achievement triggers
│   ├── seed.py            # DB init + idempotent sample-data seeding
│   └── routers/
│       ├── users.py       # create user, dashboard
│       ├── enrollments.py # enroll, complete-lesson
│       └── analytics.py   # leaderboard
├── requirements.txt
└── README.md
```

## Setup

Requires **Python 3.10+** (developed/tested against 3.12).

```bash
# 1. (recommended) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt
```

## Initialise the database

The database (`edutrack.db`) is created and seeded **automatically** the first
time the server starts. To do it manually beforehand:

```bash
python -m app.seed
```

This creates the tables and inserts 3 sample courses — Python Basics (5 lessons),
Intro to FastAPI (3 lessons), SQL 101 (10 lessons) — plus two demo users. Seeding
is idempotent; re-running it will not create duplicates. To start fresh, delete
`edutrack.db` and run again.

## Run the server

```bash
uvicorn app.main:app --reload
```

- Interactive docs (Swagger UI): http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

## API reference

| Method | Path                                          | Description |
|--------|-----------------------------------------------|-------------|
| GET    | `/courses`                                    | List available courses |
| POST   | `/users`                                      | Create a user |
| POST   | `/enrollments`                                | Enroll a user in a course (blocks duplicate active enrollments) |
| POST   | `/enrollments/{enrollment_id}/complete-lesson`| Complete one lesson; auto-completes the course and unlocks achievements |
| GET    | `/users/{user_id}/dashboard`                  | User profile + active-course progress (%) + achievements |
| GET    | `/analytics/leaderboard`                      | Top 5 users by total lessons completed |

### Achievement rules (handled inside `complete-lesson`)

- **Fast Starter** — awarded when a user completes their first-ever course.
- **Deep Diver** — awarded when a user completes a course with 10 or more lessons.

Both can be unlocked at once (e.g. a user's first course is a 10-lesson one).
Achievements are never granted twice.

### Status codes

- `201 Created` — user/enrollment created
- `200 OK` — successful reads and lesson completions
- `400 Bad Request` — duplicate active enrollment, or completing a lesson on an
  already-finished course
- `404 Not Found` — unknown user, course, or enrollment id
- `422 Unprocessable Entity` — request body fails Pydantic validation

## Quick walkthrough (curl)

```bash
# enroll demo user 1 in SQL 101 (course 3, 10 lessons)
curl -X POST localhost:8000/enrollments \
  -H 'Content-Type: application/json' \
  -d '{"user_id": 1, "course_id": 3}'

# complete a lesson (repeat 10x to finish the course)
curl -X POST localhost:8000/enrollments/1/complete-lesson

# view the dashboard
curl localhost:8000/users/1/dashboard

# leaderboard
curl localhost:8000/analytics/leaderboard
```

## Design notes

- **Separation of concerns.** Routers only translate HTTP <-> service calls.
  All business logic lives in `crud.py` and raises a `ServiceError` carrying an
  HTTP status, which routers convert to `HTTPException` — this keeps FastAPI out
  of the service layer and makes the logic unit-testable.
- **Duplicate-enrollment safety** is enforced both in code and by a *partial*
  unique index (`unique (user_id, course_id) where status = 'active'`), so
  completed enrollments can repeat if a user re-takes a course.
- **Leaderboard** uses a single SQL aggregation
  (`SUM(...) ... GROUP BY ... ORDER BY ... LIMIT 5`) — no Python-side sorting.
- Timestamps are stored timezone-aware in UTC.
