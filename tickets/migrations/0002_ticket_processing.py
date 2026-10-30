from django.db import migrations, models
import tickets.phones


def populate_phone(apps, schema_editor):
    Ticket = apps.get_model("tickets", "Ticket")
    for ticket in Ticket.objects.all().iterator():
        normalized = tickets.phones.normalize_phone(ticket.phone)
        Ticket.objects.filter(pk=ticket.pk).update(phone_normalized=normalized)


class Migration(migrations.Migration):
    dependencies = [("tickets", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="ticket", name="phone_normalized",
            field=models.CharField(blank=True, db_index=True, max_length=12, verbose_name="Телефон для поиска"),
        ),
        migrations.AddField(
            model_name="ticket", name="status",
            field=models.CharField(choices=[("new", "Новая"), ("in_progress", "В работе"), ("closed", "Закрыта")], default="new", max_length=20, verbose_name="Статус"),
        ),
        migrations.AddField(
            model_name="ticket", name="manager_comment",
            field=models.TextField(blank=True, verbose_name="Комментарий менеджера"),
        ),
        migrations.RunPython(populate_phone, migrations.RunPython.noop),
    ]
