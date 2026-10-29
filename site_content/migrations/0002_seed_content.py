from django.db import migrations


def seed_content(apps, schema_editor):
    SiteSettings = apps.get_model("site_content", "SiteSettings")
    Case = apps.get_model("site_content", "Case")
    FAQ = apps.get_model("site_content", "FAQ")
    CustomerLogo = apps.get_model("site_content", "CustomerLogo")

    SiteSettings.objects.update_or_create(pk=1, defaults={
        "phone": "+7 (904) 626 06 94",
        "work_hours": "Ежедневно 9:00–18:00",
        "email": "info@montazh-imperia.ru",
        "address": "г. Владивосток, Приморский край",
        "legal_name": "ООО «МОНТАЖНАЯ ИМПЕРИЯ»",
        "inn": "2536242742",
        "ogrn": "1112536007210",
        "seo_title": "Системы безопасности и электрика во Владивостоке — Монтажная Империя",
        "seo_description": "Проектирование, монтаж и настройка видеонаблюдения, СКУД, сигнализации и электрики во Владивостоке. Системы защиты под ключ для бизнеса и частных клиентов.",
    })

    for order, image in enumerate(("img/administrativeobjects.webp", "img/socialobjects.png", "img/businesssberbank.png"), start=1):
        Case.objects.create(
            title="Бизнес-центр Сбербанка",
            tags="Видеонаблюдение, СКУД",
            status_text="Объект сдан · на обслуживании",
            description="Комплексная система безопасности класса А: 48 IP-камер с видеоаналитикой, СКУД на 6 входных групп и интеграция с постом охраны.",
            metric_1_value="48", metric_1_label="IP-камер",
            metric_2_value="14 дн", metric_2_label="Срок сдачи",
            metric_3_value="6", metric_3_label="Точек СКУД",
            initial_image=image, order=order,
        )

    questions = (
        ("ВЫЕЗД ИНЖЕНЕРА ДЕЙСТВИТЕЛЬНО БЕСПЛАТНЫЙ?", "Да, инженер бесплатно приедет на объект, проведёт осмотр и поможет определить необходимое оборудование."),
        ("У НАС НЕТ ПРОЕКТА. СДЕЛАЕТЕ САМИ?", "Да, мы можем разработать проект с нуля."),
        ("У НАС УЖЕ СТОИТ СИСТЕМА. ВОЗЬМЁТЕСЬ?", "Да, работаем с уже установленными системами."),
        ("КАКАЯ ГАРАНТИЯ НА РАБОТЫ?", "Условия гарантии зависят от выполненных работ."),
        ("КАК МОЖНО ОПЛАТИТЬ?", "Доступные способы оплаты уточняются при заключении договора."),
    )
    for order, (question, answer) in enumerate(questions, start=1):
        FAQ.objects.create(question=question, answer=answer, order=order)

    logos = (
        ("Сбербанк", "img/sponsors/sber.png"),
        ("МЧС России", "img/sponsors/mchs.png"),
        ("Газпром", "img/sponsors/gazprom.png"),
        ("Т-Банк", "img/sponsors/tbank.png"),
        ("ФССП России", "img/sponsors/fssp.png"),
    )
    for order, (name, image) in enumerate(logos, start=1):
        CustomerLogo.objects.create(name=name, initial_image=image, order=order)


class Migration(migrations.Migration):
    dependencies = [("site_content", "0001_initial")]
    operations = [migrations.RunPython(seed_content, migrations.RunPython.noop)]
