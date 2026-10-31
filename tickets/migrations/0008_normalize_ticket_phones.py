from django.db import migrations

from tickets.phones import normalize_phone


def normalize_existing_phones(apps, schema_editor):
    Ticket = apps.get_model("tickets", "Ticket")
    tickets = Ticket.objects.using(schema_editor.connection.alias)
    for ticket in tickets.all().iterator():
        normalized = normalize_phone(ticket.phone)
        if normalized and (ticket.phone != normalized or ticket.phone_normalized != normalized):
            tickets.filter(pk=ticket.pk).update(phone=normalized, phone_normalized=normalized)


class Migration(migrations.Migration):
    dependencies = [("tickets", "0007_merge_email_notifications")]

    operations = [migrations.RunPython(normalize_existing_phones, migrations.RunPython.noop)]
