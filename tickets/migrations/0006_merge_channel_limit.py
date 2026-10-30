from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0004_merge_notification_manager"),
        ("tickets", "0005_seed_notification_channels"),
    ]
    operations = []
