from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0003_merge_consent_processing"),
        ("tickets", "0003_seed_notification_settings"),
        ("tickets", "0003_ticket_assignee"),
    ]

    operations = []
