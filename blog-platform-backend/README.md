# Blog Platform Backend

A full-featured blogging platform backend built with **FastAPI** + **PostgreSQL**.

Tested end-to-end (auth, RBAC, posts, tags, categories, comments, search, pagination,
rate limiting, soft delete) — see `tests/smoke_test.py`.

## Features

- **Auth & Authorization**: JWT access/refresh tokens, bcrypt password hashing, roles
  (`user`, `author`, `admin`) chosen at registration, role-based endpoint protection
- **Posts**: create/read/update/delete, draft/published/archived status, auto slug
  generation, view count tracking, soft delete
- **Categories** (One-to-Many with posts) and **Tags** (Many-to-Many with posts)
- **Search & pagination**: search posts by title, content, or tag name; paginated results
- **Comments**: nested replies (self-referential FK, arbitrary depth), rate-limited
  (default 5/minute per IP) to prevent spam
- **Firebase (optional)**: push notifications on new comments/replies, Cloud Storage
  uploads, Firebase Auth token verification — all no-ops if not configured, so the
  core API works fine without any Firebase setup
- **Error handling**: centralized handlers for validation errors, DB errors, and
  unexpected exceptions, all wrapped in try/except at the route level

## Project Structure

```
blog-platform-backend/
├── app/
│   ├── main.py                # FastAPI app, middleware, error handlers, router registration
│   ├── config.py               # Settings (env vars)
│   ├── database.py             # SQLAlchemy engine/session
│   ├── models/                 # SQLAlchemy ORM models (User, Post, Category, Tag, Comment)
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── crud/                    # DB access layer (business logic)
│   ├── routers/                 # API route handlers (auth, users, posts, categories, tags, comments)
│   ├── core/                    # security.py (JWT/bcrypt), deps.py (auth deps), rate_limiter.py
│   ├── utils/slug.py            # Unique slug generation
│   └── firebase/                 # Optional Firebase Admin SDK integration
├── tests/smoke_test.py          # End-to-end smoke test (40+ assertions)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml            # Postgres + API, one command to run everything
├── .env.example
└── README.md
```

## Database Design

- `users` 1—N `posts` (author)
- `categories` 1—N `posts`
- `posts` N—N `tags` (via `post_tags` association table)
- `posts` 1—N `comments`
- `comments` 1—N `comments` (self-referential, for nested replies)
- Soft delete flags (`is_deleted`) on `users`, `posts`, `comments`; `is_archived` on `posts`

## Quick Start (Docker — recommended, includes PostgreSQL)

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`. PostgreSQL runs in its own container automatically —
nothing else to install.

## Quick Start (Local Python, without Docker)

1. **Install PostgreSQL** locally and create a database, OR skip Postgres entirely
   for quick testing by using SQLite (see step 3).

2. **Install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set `DATABASE_URL` and a strong, random `SECRET_KEY` (at least
   32 characters):
   - PostgreSQL: `postgresql://blog_user:blog_password@localhost:5432/blog_db`
     (create the user/db first, or use `docker compose up db` to just run Postgres)
   - SQLite (zero setup, fine for local testing): `sqlite:///./blog.db`

4. **Run the server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Tables are created automatically on startup (`Base.metadata.create_all`).

5. **Open the interactive API docs**: http://localhost:8000/docs

## Running the Smoke Test

With the server running (either via Docker or locally) at `http://localhost:8000`:

```bash
pip install httpx   # if not already installed
python3 tests/smoke_test.py
```

This registers users of every role, logs in, creates categories/posts/tags,
verifies public vs. author vs. admin visibility rules, tests search and
pagination, checks view-count tracking, publishes/archives posts, creates
nested comment replies, verifies rate limiting kicks in, and tests soft
delete — printing PASS/FAIL for every check.

> Note: the smoke test uses a fresh, empty database. Re-running it against a
> database that already has `admin1`/`author1`/etc. will fail on duplicate
> registration — delete `blog.db` (SQLite) or restart the `db` container
> (Docker) between runs.

## API Overview

All endpoints are prefixed with `/api`. Full interactive documentation
(with request/response schemas) is available at `/docs` once running.

| Area | Endpoint | Notes |
|---|---|---|
| Auth | `POST /api/auth/register` | role (`user`/`author`/`admin`) passed at registration |
| Auth | `POST /api/auth/login` | OAuth2 form login, returns access + refresh token |
| Auth | `POST /api/auth/refresh` | exchange refresh token for new tokens |
| Users | `GET /api/users/me` | current user profile |
| Users | `GET /api/users` | admin only |
| Users | `PATCH /api/users/{id}/role` | admin only |
| Users | `DELETE /api/users/{id}` | soft delete; self or admin |
| Posts | `GET /api/posts` | pagination + `search`, `category_id`, `tag`, `status` filters |
| Posts | `GET /api/posts/{slug_or_id}` | increments view count for published posts |
| Posts | `POST /api/posts` | author/admin only |
| Posts | `PUT /api/posts/{id}` | owner/admin only |
| Posts | `PATCH /api/posts/{id}/status` | publish/draft/archive |
| Posts | `POST /api/posts/{id}/archive` \| `/unarchive` | |
| Posts | `DELETE /api/posts/{id}` | soft delete |
| Categories | `GET/POST/PATCH/DELETE /api/categories` | write ops need author/admin |
| Tags | `GET /api/tags` | tags are created implicitly via posts |
| Comments | `GET/POST /api/posts/{post_id}/comments` | POST is rate-limited, supports `parent_id` for replies |
| Comments | `PATCH/DELETE /api/posts/{post_id}/comments/{id}` | owner/admin only |

## Authentication in Swagger UI

Click **Authorize** in `/docs`, then log in with a username/password from
`/api/auth/register` — Swagger's OAuth2 form matches `/api/auth/login` directly.

## Enabling Firebase (optional)

Firebase is fully optional — the app runs and passes all tests without it.
To enable push notifications / storage uploads:

1. Create a Firebase project and download a service account JSON key.
2. Set in `.env`:
   ```
   FIREBASE_CREDENTIALS_PATH=/path/to/service-account.json
   FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   ```
3. Restart the app. `app/firebase/notifications.py` will then send real FCM
   push notifications when a post's author has a `firebase_uid`/device token
   linked (store a device token on the `User` model as needed for your client).

## Production Notes

- Swap `Base.metadata.create_all()` for **Alembic migrations** in production
  (this project ships without Alembic wiring to keep setup to one step, but
  the models are ready for it — run `alembic init` and generate an initial
  revision from `app.database.Base.metadata`).
- Set a strong, random `SECRET_KEY`.
- Restrict CORS `allow_origins` instead of `*`.
- Put the API behind a reverse proxy (e.g. Nginx) with TLS.


1.i want frontend for this backend code base
2.in id column id is not readable (3ddcf18e-5c8c-49e6-82cd-dda8263497bf) i want numeric style
3.there is 2 time logins , i want log in from endpoint and then generated jwt to be used for authorization instead of giving username and password in authorization form