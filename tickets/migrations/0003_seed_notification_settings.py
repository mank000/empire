from django.db import migrations


def seed_settings(apps, schema_editor):
    NotificationSettings = apps.get_model("tickets", "NotificationSettings")
    NotificationSettings.objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("tickets", "0002_notificationsettings_notificationdelivery")]
    operations = [migrations.RunPython(seed_settings, migrations.RunPython.noop)]
