# SafeNotes

SafeNotes is a university prototype (CI3064 Desarrollo Seguro) for a secure
notes-taking application. It implements role-based access control (Admin /
Editor / Lector), notes with content encrypted at rest, note sharing between
users, personal folders for organizing shared notes, and an audit log that
records security-relevant events (logins, logouts, lockouts, admin actions).

The app is split into two independent servers:

- A **Django REST Framework API** (JWT authentication) that owns all data
  and business logic, served at `http://127.0.0.1:8000/api/`.
- A **React (Vite) single-page app** that consumes that API, served at
  `http://localhost:5173` in development.

The full formal write-up of the design and security decisions lives in the
separate report deliverable, not in this README.

## Backend setup

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Edit `.env` and set:

- `DJANGO_SECRET_KEY` — any long random string (local/demo use only).
- `DJANGO_DEBUG` — `True` for local development.
- `DJANGO_ALLOWED_HOSTS` — e.g. `127.0.0.1,localhost`.
- `NOTES_ENCRYPTION_KEY` — used to encrypt note content at rest. Generate
  one with:

  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

Then apply migrations and seed demo data:

```bash
python manage.py migrate
python manage.py seed_demo_data
```

`seed_demo_data` is idempotent — running it again updates the same demo
rows instead of duplicating them, and prints the demo credentials to
stdout.

Finally, start the API server:

```bash
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/api/`. There is no
server-rendered UI at `/` — the app is consumed entirely through the React
frontend below (or directly via the API).

## Frontend setup

In a second terminal:

```bash
cd frontend
cp .env.example .env
```

`.env` sets `VITE_API_BASE_URL` (defaults to
`http://127.0.0.1:8000/api/`, matching the backend above).

```bash
npm install
npm run dev
```

The SPA is served at `http://localhost:5173` (Vite's default) and talks to
the Django API over HTTP using JWT access/refresh tokens.

## Demo credentials

All seeded demo accounts share the same password: **`SafeNotes2026!`**

| Username     | Password          | Role   |
|--------------|-------------------|--------|
| `admin_demo` | `SafeNotes2026!`  | Admin  |
| `editor1`    | `SafeNotes2026!`  | Editor |
| `editor2`    | `SafeNotes2026!`  | Editor |
| `lector1`    | `SafeNotes2026!`  | Lector |
| `lector2`    | `SafeNotes2026!`  | Lector |

## Where to click, per role

After logging in through the React app, each role uses a different set of
routes:

- **Admin** (`admin_demo`) -> `/admin`
  User management (create users, toggle active, change role), category
  CRUD, and the audit log.
- **Editor** (`editor1`, `editor2`) -> `/notes`
  Their own notes: create, edit, delete, and share notes with Lector
  accounts.
- **Lector** (`lector1`, `lector2`) -> `/shared` and `/folders`
  Notes shared with them (read-only) and personal folders for organizing
  those shared notes.

## Running tests

Backend:

```bash
python manage.py test
```

There are no automated frontend tests — verifying the React app is out of
scope for this project and was instead done manually against the live API.
