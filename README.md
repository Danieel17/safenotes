# SafeNotes

A university prototype for CI3064 Desarrollo Seguro.

## Getting started

After setting up the environment and running migrations for the first time,
create the initial Admin account:

```
python manage.py createsuperuser
```

This is currently the only way to get an Admin-role user into the system
(the automated demo data seeder is a later ticket). You can inspect or
change a user's role afterward via `/admin/` or the Django shell.

A fuller README (setup, environment variables, running tests) will be
added in a later ticket.
