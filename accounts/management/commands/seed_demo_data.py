from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from notes.models import Category, Folder, FolderItem, Note, Share

DEMO_PASSWORD = "SafeNotes2026!"

# Fixed, recognizable usernames used to identify (and re-seed) demo data.
ADMIN_USERNAME = "admin_demo"
EDITOR_USERNAMES = ["editor1", "editor2"]
LECTOR_USERNAMES = ["lector1", "lector2"]

CATEGORY_NAMES = ["Trabajo", "Personal", "Estudios"]

NOTES_DATA = {
    "editor1": [
        (
            "Plan de sprint",
            "Revisar el backlog del proyecto SafeNotes y priorizar las tareas de "
            "seguridad pendientes antes de la reunion del viernes.",
            "Trabajo",
        ),
        (
            "Lista de compras",
            "Comprar cafe, pan integral y frutas para la semana. No olvidar "
            "detergente para la ropa.",
            "Personal",
        ),
        (
            "Resumen de criptografia",
            "Repasar el funcionamiento de Fernet (AES en modo CBC + HMAC) antes "
            "del examen de Desarrollo Seguro.",
            "Estudios",
        ),
    ],
    "editor2": [
        (
            "Reunion con el cliente",
            "Preparar la demo del modulo de auditoria y anotar los comentarios "
            "del cliente sobre el flujo de login.",
            "Trabajo",
        ),
        (
            "Ideas para el fin de semana",
            "Salir a caminar por el cerro el sabado y juntarse con la familia "
            "el domingo para almorzar.",
            "Personal",
        ),
        (
            "Apuntes de bases de datos",
            "Repasar normalizacion (1FN, 2FN, 3FN) y transacciones ACID para el "
            "control de la proxima semana.",
            "Estudios",
        ),
    ],
}


class Command(BaseCommand):
    help = (
        "Seeds SafeNotes with a fixed, recognizable set of demo accounts, "
        "categories, notes, shares and folders for grading/demo purposes. "
        "Idempotent: re-running it updates the same rows instead of "
        "duplicating them."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        created_summary = {
            "users": 0,
            "categories": 0,
            "notes": 0,
            "shares": 0,
            "folders": 0,
        }

        # --- Users ---------------------------------------------------
        admin_user, created = self._get_or_create_user(
            ADMIN_USERNAME, User.ROLE_ADMIN, email="admin_demo@safenotes.local"
        )
        created_summary["users"] += created
        self._report_user(admin_user, User.ROLE_ADMIN)

        editors = []
        for username in EDITOR_USERNAMES:
            user, created = self._get_or_create_user(
                username, User.ROLE_EDITOR, email=f"{username}@safenotes.local"
            )
            created_summary["users"] += created
            editors.append(user)
            self._report_user(user, User.ROLE_EDITOR)

        lectors = []
        for username in LECTOR_USERNAMES:
            user, created = self._get_or_create_user(
                username, User.ROLE_LECTOR, email=f"{username}@safenotes.local"
            )
            created_summary["users"] += created
            lectors.append(user)
            self._report_user(user, User.ROLE_LECTOR)

        # --- Categories ------------------------------------------------
        categories = {}
        for name in CATEGORY_NAMES:
            category, created = Category.objects.get_or_create(
                name=name, defaults={"created_by": admin_user}
            )
            created_summary["categories"] += created
            categories[name] = category

        # --- Notes -------------------------------------------------------
        notes_by_editor = {}
        for username, notes_data in NOTES_DATA.items():
            owner = User.objects.get(username=username)
            owner_notes = []
            for title, content, category_name in notes_data:
                note, created = Note.objects.update_or_create(
                    owner=owner,
                    title=title,
                    defaults={
                        "content": content,
                        "category": categories[category_name],
                    },
                )
                created_summary["notes"] += created
                owner_notes.append(note)
            notes_by_editor[username] = owner_notes

        # --- Shares ----------------------------------------------------
        # editor1's first note -> shared with both lectors (visible multi-share)
        # editor1's second note -> shared with lector1
        # editor2's first note -> shared with lector2
        editor1_notes = notes_by_editor["editor1"]
        editor2_notes = notes_by_editor["editor2"]
        lector1, lector2 = lectors

        share_specs = [
            (editor1_notes[0], lector1),
            (editor1_notes[0], lector2),
            (editor1_notes[1], lector1),
            (editor2_notes[0], lector2),
        ]

        shares_by_lector = {lector1.username: [], lector2.username: []}
        for note, lector in share_specs:
            share, created = Share.objects.get_or_create(note=note, shared_with=lector)
            created_summary["shares"] += created
            shares_by_lector[lector.username].append(share)

        # --- Folders + FolderItems --------------------------------------
        for lector in lectors:
            folder, created = Folder.objects.get_or_create(
                owner=lector, name="Mis compartidas"
            )
            created_summary["folders"] += created
            for share in shares_by_lector[lector.username]:
                FolderItem.objects.get_or_create(folder=folder, share=share)

        # --- Summary -----------------------------------------------------
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("SafeNotes demo data seeded."))
        self.stdout.write(f"Shared demo password for all seeded accounts: {DEMO_PASSWORD}")
        self.stdout.write(
            "Summary (newly created this run): "
            f"users={created_summary['users']}, "
            f"categories={created_summary['categories']}, "
            f"notes={created_summary['notes']}, "
            f"shares={created_summary['shares']}, "
            f"folders={created_summary['folders']}"
        )

    def _get_or_create_user(self, username, role, email=""):
        """Get or create a demo user with the fixed demo password and role.

        Uses get_or_create + an explicit password/role sync on every run so
        the command is idempotent (safe to re-run) while still guaranteeing
        the documented credentials work even if the row already existed.
        """
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"role": role, "is_active": True, "email": email},
        )
        # Keep role/password/active status/email in sync even on re-runs, in
        # case a previous run or manual edit left them in an unexpected state.
        user.role = role
        user.is_active = True
        user.email = email
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user, created

    def _report_user(self, user, role):
        self.stdout.write(f"  {user.username} (role={role}) password={DEMO_PASSWORD}")
