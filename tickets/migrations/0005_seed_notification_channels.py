from django.db import migrations


def seed_channels(apps, schema_editor):
    ChannelState = apps.get_model("tickets", "NotificationChannelState")
    for channel in ("telegram", "max"):
        ChannelState.objects.using(schema_editor.connection.alias).get_or_create(channel=channel)


class Migration(migrations.Migration):
    dependencies = [("tickets", "0004_notificationchannelstate_and_more")]
    operations = [migrations.RunPython(seed_channels, migrations.RunPython.noop)]
