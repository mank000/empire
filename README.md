# Монтажная Империя

Сайт компании на Django. Контент главной редактируется в админке. Заявки сохраняются в SQLite, обрабатываются менеджерами в админке и отправляются через настроенные каналы уведомлений.

## Стек

- Python 3.13, Django 6.1.2;
- HTML-шаблоны Django, CSS и JavaScript без фронтенд-фреймворка;
- SQLite для заявок, контента и очереди ожидающих уведомлений;
- Redis для кеша главной и брокера Celery; Celery worker для отправки уведомлений;
- Gunicorn и Nginx в production-конфигурации;
- Docker Compose для локального и production-запуска.

Версии Python-зависимостей указаны в `requirements.txt` и `requirements-dev.txt`.

## Структура проекта

| Путь                         | Назначение                                                               |
| ---------------------------- | ------------------------------------------------------------------------ |
| `mantage_empire/settings.py` | Настройки Django и переменные окружения                                  |
| `mantage_empire/urls.py`     | Маршруты главной, API, админки, `robots.txt` и `sitemap.xml`             |
| `mantage_empire/views.py`    | Приём и сохранение заявок                                                |
| `tickets/`                   | Заявки, менеджеры, уведомления, миграции и тесты                         |
| `site_content/`              | Редактируемый контент главной и его кеширование                          |
| `templates/`                 | Базовый шаблон, главная, страница 404 и секции                           |
| `static/`                    | Исходные CSS, JavaScript, изображения, шрифты и видео                    |
| `staticfiles/`               | Результат `collectstatic`; генерируется при сборке и не хранится в Git   |
| `compose.yaml`               | Локальная разработка в контейнере                                        |
| `compose.prod.yaml`          | Gunicorn, Nginx, Redis, worker, dispatcher и резервные копии            |
| `deploy/`                    | Конфигурация Nginx, точка входа контейнера и инструкция по развёртыванию |

## Локальный запуск без Docker

Нужен Python 3.13. В PowerShell из корня репозитория:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:DJANGO_DEBUG = "true"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Сайт будет доступен по адресу `http://127.0.0.1:8000/`. Для входа в админку создайте учётную запись:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Админка находится по адресу `/admin/`. По умолчанию `DJANGO_DEBUG=false`; для локального запуска без Docker установите `DJANGO_DEBUG=true`, как в примере выше. В dev без `DJANGO_SECRET_KEY` Django создаёт временный ключ при запуске. Данные сохраняются в `db.sqlite3` в корне проекта, если `DJANGO_DB_PATH` не переопределён. `runserver` запускает сайт без фоновой отправки; для проверки уведомлений запустите Redis, Celery worker и `python manage.py dispatch_notifications` либо используйте Docker Compose ниже.

## Локальный запуск через Docker

Нужны Docker Engine и Docker Compose:

```sh
docker compose up --build
```

Откройте `http://localhost:8000/`. Compose запускает сайт, Redis, worker и dispatcher. Код подключён как локальная папка, включены `DEBUG` и `django-browser-reload`. База хранится в томе `dev_database`. В dev токены Telegram и MAX сохраняются с префиксом `dev-plaintext:` и не требуют Fernet-ключа; такие токены не работают в production. Для остановки используйте `docker compose down`.

### Локальная проверка с `DEBUG=false`

В `compose.prod.yaml` задано `DJANGO_DEBUG=false`. При этом Django перенаправляет HTTP на HTTPS, а Nginx не запустится без сертификата. Для обычной локальной разработки выше сертификат не нужен; следующие команды нужны только для проверки production-режима. Выполняйте их в отдельной локальной копии проекта, чтобы не смешивать тестовый сертификат с сертификатом сервера.

1. Создайте `.env` из `.env.example`, если файла ещё нет: `test -f .env || cp .env.example .env`. Укажите случайный `DJANGO_SECRET_KEY` (например, результат `openssl rand -hex 32`) и локальные значения:

   ```dotenv
   DJANGO_DEBUG=false
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
   DJANGO_CSRF_TRUSTED_ORIGINS=https://localhost
   DJANGO_PUBLIC_SITE_URL=https://localhost
   ```

   Если `.env` уже существует, не перезаписывайте его без проверки.

2. Если сертификата в `deploy/letsencrypt/live/empire/` ещё нет, создайте самоподписанный сертификат для локального теста. Не выполняйте эту команду поверх существующего сертификата: она перезапишет ключ.

   ```sh
   mkdir -p deploy/letsencrypt/live/empire
   openssl req -x509 -newkey rsa:2048 -nodes -days 7 \
     -keyout deploy/letsencrypt/live/empire/privkey.pem \
     -out deploy/letsencrypt/live/empire/fullchain.pem \
     -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost"
   ```

3. Запустите отдельный Compose-проект, чтобы не заменить работающий dev-контейнер, и проверьте ответ:

   ```sh
   docker compose -p empire-local-prod -f compose.prod.yaml up --build -d
   curl -kI https://localhost/
   ```

   Порты 80 и 443 должны быть свободны. Браузер предупредит о недоверенном самоподписанном сертификате; `curl -k` подходит для локальной проверки. Для остановки: `docker compose -p empire-local-prod -f compose.prod.yaml down`. Certbot и `nginx-bootstrap` здесь не нужны: порядок получения настоящего сертификата для сервера описан в [deploy/README.md](deploy/README.md).

## Переменные окружения

| Переменная                    | Назначение                                                                                                       |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `DJANGO_DEBUG`                | По умолчанию `false`; для разработки задайте `true` явно, в `compose.prod.yaml` закреплено `false`               |
| `DJANGO_SECRET_KEY`           | Секрет Django; обязателен при `DEBUG=false`                                                                      |
| `DJANGO_ALLOWED_HOSTS`        | Список разрешённых доменов через запятую; обязателен при `DEBUG=false`                                           |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Доверенные HTTPS-адреса для CSRF, через запятую                                                                  |
| `DJANGO_PUBLIC_SITE_URL`      | Публичный адрес сайта без завершающего `/`; используется для canonical, Open Graph, `robots.txt` и `sitemap.xml` |
| `DJANGO_DB_PATH`              | Путь к файлу SQLite; в Compose указывает на постоянный том                                                       |
| `NOTIFICATION_ENCRYPTION_KEY` | Fernet-ключ для токенов Telegram и MAX в production; в dev не нужен                                               |
| `REDIS_URL`                   | Redis для кеша главной; в Compose задан автоматически                                                               |
| `CELERY_BROKER_URL`           | Redis-брокер Celery; в Compose задан автоматически                                                                   |
| `DJANGO_FROM_EMAIL`           | Адрес отправителя почтовых уведомлений                                                                              |
| `DJANGO_SMTP_*`               | Хост, порт, логин, пароль и TLS/SSL для почтовых уведомлений                                                         |

Пример значений находится в `.env.example`. Файл `.env` читает production Compose через `env_file`; сам Django не загружает его автоматически при запуске без Docker. Настоящие секреты и сертификаты не следует добавлять в Git.

Время в админке отображается по часовому поясу `Asia/Vladivostok`. Ошибки HTTP-запросов и сообщения приложений пишутся в stdout контейнера и доступны через `docker compose logs web`.

## Как работает заявка

1. JavaScript отправляет имя, телефон и отметку согласия на `POST /api/tickets/` в JSON. CSRF-токен берётся из формы. Обе формы используют общий шаблон; до загрузки скрипта кнопка отправки отключена, чтобы браузер не отправил телефон в URL.
2. `TicketForm` проверяет поля. В одной транзакции создаются заявка, время согласия и ожидающие доставки для включённых каналов. HTTP-запрос не ждёт Telegram, MAX или SMTP.
3. API возвращает `201`, и интерфейс показывает успех. При ошибке пользователь может повторить отправку.
4. Dispatcher проверяет ожидающие доставки только при доступном Celery worker. Worker отправляет уведомления; общий лимит — одно сообщение в минуту на канал. После длительного простоя старые заявки объединяются в сводку, а сами заявки остаются в админке.
5. Суперпользователь включает Telegram, MAX и почту, задаёт токены, ID чатов и адрес получателя в «Настройках уведомлений». Для почты дополнительно нужны SMTP-параметры в `.env`. По умолчанию все каналы выключены.
6. Менеджер с отдельной учётной записью может взять заявку в работу, изменить статус и оставить комментарий. Группа «Менеджеры заявок» создаётся после миграций; учётные записи создаёт суперпользователь.

В production Nginx ограничивает `POST /api/tickets/` по IP; при превышении возвращает `429`. В dev этого ограничения нет. Подробности и порядок настройки сервисов — в [deploy/README.md](deploy/README.md).

## Проверки

Из активированного окружения или через его `python.exe`:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Для проверки deployment-настроек задайте реальные production-переменные и выполните `python manage.py check --deploy`. При текущей конфигурации остаются предупреждения о HSTS для поддоменов и preload: включать эти параметры следует только после решения по всем доменам и HTTPS.

После развёртывания вручную проверьте главную, политику, реквизиты, `/robots.txt`, `/sitemap.xml`, страницу 404, статику, отправку тестовой заявки, её появление в админке и доставку в каждый включённый канал. В sitemap входят главная, политика и реквизиты. Проверьте изменение контента в админке, мобильную вёрстку и консоль браузера.

## Развёртывание

Подробные команды и вариант запуска без Docker приведены в [deploy/README.md](deploy/README.md). Кратко для production Compose на Linux:

1. Скопируйте `.env.example` в `.env` и задайте домен, случайный `DJANGO_SECRET_KEY`, доверенные адреса, `DJANGO_PUBLIC_SITE_URL` и Fernet-ключ. Если нужна почта, укажите SMTP-параметры.
2. Выпустите сертификат через временный HTTP Nginx по инструкции в `deploy/README.md`.
3. Запустите `docker compose -f compose.prod.yaml up --build -d` и настройте ежедневный запуск `deploy/renew-certificate.sh` через cron.
4. Проверьте `docker compose -f compose.prod.yaml run --rm certbot renew --dry-run`, логи `web`, `nginx`, `redis`, `worker`, `dispatcher` и `backup`, а также `docker compose -f compose.prod.yaml exec web python manage.py check --deploy`.

При старте `web` выполняет миграции и `collectstatic`, затем запускает Gunicorn. Nginx отдаёт ACME challenge по HTTP, перенаправляет остальные HTTP-запросы на HTTPS и отдаёт статику. SQLite хранится в томе `database`, загруженные изображения — в `media`, собранная статика — в `staticfiles`, сертификаты — в `deploy/letsencrypt/`. Сервис `backup` сохраняет согласованные копии SQLite в `backups/`, оставляет 14 последних и повторяет неудачное копирование через 5 минут. Восстановление выполняйте через `deploy/restore-database.sh` по инструкции в [deploy/README.md](deploy/README.md). Команда `docker compose -f compose.prod.yaml down -v` удаляет тома вместе с заявками и загруженными файлами.

## Перед публичным запуском

- Получить у клиента согласованный текст политики конфиденциальности и опубликовать его в «Настройках сайта»: сейчас страница показывает сообщение об отсутствии текста.
- Указать настоящие токены, чаты и/или SMTP-данные, включить нужные каналы в админке и проверить доставку тестовой заявки. Без этих данных фактическая отправка не проверена.
- Ограничить доступ к каталогу `backups/`: текущие права создаваемых файлов ещё требуют доработки перед production. Копии содержат телефоны заявителей.
- Проверить восстановление копии на отдельном стенде и `certbot renew --dry-run` на сервере с рабочими DNS и портом 80.
