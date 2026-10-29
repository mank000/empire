# Монтажная Империя

Сайт компании на Django. Главная страница собрана из шаблонов секций; стили и поведение интерфейса находятся в `static/`. Посетитель может оставить имя и телефон в форме заявки. Сервер проверяет данные, сохраняет заявку в SQLite и показывает её в Django Admin.

## Стек

- Python 3.13, Django 6.1.2;
- HTML-шаблоны Django, CSS и JavaScript без фронтенд-фреймворка;
- SQLite для заявок и служебных таблиц Django;
- Gunicorn и Nginx в production-конфигурации;
- Docker Compose для локального и production-запуска.

Версии Python-зависимостей указаны в `requirements.txt` и `requirements-dev.txt`.

## Структура проекта

| Путь                         | Назначение                                                               |
| ---------------------------- | ------------------------------------------------------------------------ |
| `mantage_empire/settings.py` | Настройки Django и переменные окружения                                  |
| `mantage_empire/urls.py`     | Маршруты главной, API, админки, `robots.txt` и `sitemap.xml`             |
| `mantage_empire/views.py`    | Приём и сохранение заявок                                                |
| `tickets/`                   | Модель, проверка полей, админка, миграции и тесты заявок                 |
| `templates/`                 | Базовый шаблон, главная, страница 404 и секции                           |
| `static/`                    | Исходные CSS, JavaScript, изображения, шрифты и видео                    |
| `staticfiles/`               | Результат `collectstatic`; генерируется при сборке и не хранится в Git   |
| `compose.yaml`               | Локальная разработка в контейнере                                        |
| `compose.prod.yaml`          | Gunicorn, Nginx и постоянные тома для production                         |
| `deploy/`                    | Конфигурация Nginx, точка входа контейнера и инструкция по развёртыванию |

## Локальный запуск без Docker

Нужен Python 3.13. В PowerShell из корня репозитория:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Сайт будет доступен по адресу `http://127.0.0.1:8000/`. Для входа в админку создайте учётную запись:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Админка находится по адресу `/admin/`. При локальном запуске `DJANGO_DEBUG` по умолчанию равен `true`. Если `DJANGO_SECRET_KEY` не задан, Django создаёт временный ключ при запуске. Данные сохраняются в `db.sqlite3` в корне проекта, если `DJANGO_DB_PATH` не переопределён.

## Локальный запуск через Docker

Нужны Docker Engine и Docker Compose:

```sh
docker compose up --build
```

Откройте `http://localhost:8000/`. В этом режиме код подключён в контейнер как локальная папка, включены `DEBUG` и `django-browser-reload`. База хранится в томе `dev_database`. Для остановки используйте `docker compose down`.

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
| `DJANGO_DEBUG`                | `true` для разработки; в `compose.prod.yaml` принудительно задано `false`                                        |
| `DJANGO_SECRET_KEY`           | Секрет Django; обязателен при `DEBUG=false`                                                                      |
| `DJANGO_ALLOWED_HOSTS`        | Список разрешённых доменов через запятую; обязателен при `DEBUG=false`                                           |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Доверенные HTTPS-адреса для CSRF, через запятую                                                                  |
| `DJANGO_PUBLIC_SITE_URL`      | Публичный адрес сайта без завершающего `/`; используется для canonical, Open Graph, `robots.txt` и `sitemap.xml` |
| `DJANGO_DB_PATH`              | Путь к файлу SQLite; в Compose указывает на постоянный том                                                       |

Пример значений находится в `.env.example`. Файл `.env` читает production Compose через `env_file`; сам Django не загружает его автоматически при запуске без Docker. Настоящие секреты и сертификаты не следует добавлять в Git.

## Как работает заявка

1. JavaScript отправляет имя, телефон и отметку согласия на `POST /api/tickets/` в JSON. CSRF-токен берётся из формы.
2. `TicketForm` проверяет поля. После успешной проверки запись создаётся в таблице заявок.
3. API возвращает `201`, и только после этого интерфейс показывает сообщение об успешной отправке. При ошибке пользователь видит сообщение и может повторить попытку.
4. Заявки доступны сотруднику с доступом к Django Admin. Уведомления о новых заявках пока не настроены: админку нужно проверять вручную.

Сервер отклоняет повторную заявку с одного `REMOTE_ADDR` в течение 30 секунд. Текущее ограничение использует локальный кеш процесса; его поведение за Nginx описано в разделе «Перед публичным запуском».

## Проверки

Из активированного окружения или через его `python.exe`:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test tickets
```

Для проверки deployment-настроек задайте реальные production-переменные и выполните `python manage.py check --deploy`. При текущей конфигурации остаются предупреждения о HSTS для поддоменов и preload: включать эти параметры следует только после решения по всем доменам и HTTPS.

После развёртывания вручную проверьте главную страницу, `/robots.txt`, `/sitemap.xml`, страницу 404, загрузку `/static/`, отправку одной тестовой заявки и её появление в админке. В sitemap включена только главная страница; административные и служебные адреса туда не входят. Отдельно проверьте ошибку отправки, мобильную вёрстку и консоль браузера.

## Развёртывание

Подробные команды и вариант запуска без Docker приведены в [deploy/README.md](deploy/README.md). Кратко для production Compose на Linux:

1. Скопируйте `.env.example` в `.env` и задайте домен, случайный `DJANGO_SECRET_KEY`, доверенные адреса и `DJANGO_PUBLIC_SITE_URL`.
2. Выпустите сертификат через временный HTTP Nginx по инструкции в `deploy/README.md`.
3. Запустите `docker compose -f compose.prod.yaml up --build -d` и настройте ежедневный запуск `deploy/renew-certificate.sh` через cron.
4. Проверьте `docker compose -f compose.prod.yaml run --rm certbot renew --dry-run`, логи `web` и `nginx`, а также `docker compose -f compose.prod.yaml exec web python manage.py check --deploy`.

При старте контейнер `web` выполняет миграции и `collectstatic`, затем запускает Gunicorn. Nginx отдаёт ACME challenge по HTTP, перенаправляет остальные HTTP-запросы на HTTPS и отдаёт статику. SQLite хранится в томе `database`, собранная статика — в `staticfiles`, а сертификаты — в `deploy/letsencrypt/`. Команда `docker compose -f compose.prod.yaml down -v` удаляет тома и вместе с ними заявки; для базы нужен отдельный проверенный порядок резервного копирования и восстановления.

## Перед публичным запуском

- Настроить резервное копирование SQLite и проверку восстановления. Если заявка должна сразу попадать менеджеру, добавить уведомление: сейчас она только сохраняется в админке.
