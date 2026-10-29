from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate, dispatch_uid="tickets.create_manager_group")
def create_manager_group(sender, **kwargs):
    if sender.name != "tickets":
        return
    group, _ = Group.objects.get_or_create(name="Менеджеры заявок")
    permissions = Permission.objects.filter(
        content_type__app_label="tickets",
        content_type__model="ticket",
        codename__in=("view_ticket", "change_ticket"),
    )
    group.permissions.set(permissions)
