from django.db import models
from django.core.exceptions import ValidationError


class SiteSettings(models.Model):
    phone = models.CharField("Телефон", max_length=30)
    work_hours = models.CharField("Часы работы", max_length=100)
    email = models.EmailField("Электронная почта")
    address = models.CharField("Адрес", max_length=255)
    telegram_url = models.URLField("Ссылка на Telegram", blank=True)
    whatsapp_url = models.URLField("Ссылка на WhatsApp", blank=True)
    legal_name = models.CharField("Название юрлица", max_length=255)
    inn = models.CharField("ИНН", max_length=12)
    ogrn = models.CharField("ОГРН", max_length=15)
    seo_title = models.CharField("SEO-заголовок главной", max_length=255)
    seo_description = models.TextField("SEO-описание главной")
    privacy_policy = models.TextField("Текст политики конфиденциальности", blank=True)

    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @property
    def phone_href(self):
        digits = "".join(character for character in self.phone if character.isdigit())
        if len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        return "+" + digits if digits else ""

    def __str__(self):
        return "Настройки сайта"


class Case(models.Model):
    title = models.CharField("Заголовок", max_length=255)
    tags = models.CharField("Теги через запятую", max_length=255, blank=True)
    status_text = models.CharField("Статус объекта", max_length=150, blank=True)
    description = models.TextField("Описание")
    metric_1_value = models.CharField("Показатель 1", max_length=50)
    metric_1_label = models.CharField("Подпись 1", max_length=100)
    metric_2_value = models.CharField("Показатель 2", max_length=50)
    metric_2_label = models.CharField("Подпись 2", max_length=100)
    metric_3_value = models.CharField("Показатель 3", max_length=50)
    metric_3_label = models.CharField("Подпись 3", max_length=100)
    photo = models.ImageField("Фото", upload_to="cases/", blank=True)
    initial_image = models.CharField("Исходное фото из статики", max_length=255, blank=True)
    order = models.PositiveIntegerField("Порядок", default=0)
    is_visible = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ("order", "pk")
        verbose_name = "Кейс"
        verbose_name_plural = "Кейсы"

    @property
    def tag_list(self):
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    def clean(self):
        if not self.photo and not self.initial_image:
            raise ValidationError({"photo": "Загрузите фото кейса."})

    def __str__(self):
        return self.title


class FAQ(models.Model):
    question = models.CharField("Вопрос", max_length=255)
    answer = models.TextField("Ответ")
    order = models.PositiveIntegerField("Порядок", default=0)
    is_visible = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ("order", "pk")
        verbose_name = "Вопрос FAQ"
        verbose_name_plural = "Вопросы FAQ"

    def __str__(self):
        return self.question


class CustomerLogo(models.Model):
    name = models.CharField("Заказчик", max_length=100)
    image = models.ImageField("Логотип", upload_to="customers/", blank=True)
    initial_image = models.CharField("Исходный логотип из статики", max_length=255, blank=True)
    order = models.PositiveIntegerField("Порядок", default=0)
    is_visible = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ("order", "pk")
        verbose_name = "Логотип заказчика"
        verbose_name_plural = "Логотипы заказчиков"

    def clean(self):
        if not self.image and not self.initial_image:
            raise ValidationError({"image": "Загрузите логотип."})

    def __str__(self):
        return self.name
