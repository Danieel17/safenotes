# SafeNotes

SafeNotes is a university prototype (CI3064 Desarrollo Seguro) for a secure
notes-taking application. It implements role-based access control (Admin /
Editor / Lector), notes with content encrypted at rest, note sharing between
users, personal folders for organizing shared notes, and an audit log that
records security-relevant events (logins, logouts, lockouts, admin actions).
The full formal write-up of the design and security decisions lives in the
separate report deliverable, not in this README.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Edit `.env` and fill in a real `NOTES_ENCRYPTION_KEY` (used to encrypt note
content at rest). Generate one with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the printed value as `NOTES_ENCRYPTION_KEY` in `.env`. Also set a real
`DJANGO_SECRET_KEY` (any long random string works for local/demo use).

Then apply migrations:

```bash
python manage.py migrate
```

The repository ships with a pre-seeded `db.sqlite3` (see credentials table
below), so this step is usually a no-op. If you want to regenerate the demo
data from scratch (or you're starting from a fresh database), run:

```bash
python manage.py seed_demo_data
```

This command is idempotent — running it again updates the same demo rows
instead of duplicating them, and prints the demo credentials to stdout.

Finally, start the dev server:

```bash
python manage.py runserver
```

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

After logging in at `/login/`, each role is redirected to its own landing
page:

- **Admin** (`admin_demo`) -> `/admin-panel/`
  User management (create users, toggle active, change role), Category
  CRUD (`/notes/categories/`), and the audit log (`/audit/`).
- **Editor** (`editor1`, `editor2`) -> `/notes/`
  Their own notes: create, edit, delete, and share notes with Lector
  accounts (`/notes/<id>/share/`).
- **Lector** (`lector1`, `lector2`) -> `/notes/shared/`
  Notes shared with them (read-only), plus personal folders
  (`/notes/folders/`) for organizing those shared notes.

## Running tests

```bash
python manage.py test
```
