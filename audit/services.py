from .models import AuditLog


def log_action(actor, action, target_repr="", request=None):
    """Create a single AuditLog row.

    This is the ONLY place that should construct AuditLog.objects.create(...)
    - callers elsewhere must go through this function so IP extraction and
    field population stay consistent.
    """
    ip_address = None
    if request is not None:
        ip_address = request.META.get("REMOTE_ADDR")

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_repr=target_repr,
        ip_address=ip_address,
    )
