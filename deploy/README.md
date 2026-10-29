# Развёртывание на Linux

## Docker Compose: локальная разработка

Запустите `docker compose up --build`. Откройте `http://localhost:8000/`. Сертификат и `.env` не нужны: используется `runserver`, `DEBUG=true` и `django-browser-reload`. Код подключён как локальная папка, поэтому изменения видны в контейнере. База хранится в отдельном томе `dev_database`.

## Docker Compose: production

1. Скопируйте `.env.example` в `.env`, задайте реальный домен и случайный `DJANGO_SECRET_KEY` (команда для генерации ниже). `.env` исключён из Git.
   Укажите канонический адрес главной в `DJANGO_PUBLIC_SITE_URL` (например, `https://example.com`), чтобы включить canonical и Open Graph метаданные и использовать этот адрес в `robots.txt` и `sitemap.xml`.
2. Выпустите сертификат по инструкции ниже. До первого выпуска основной Nginx не запустится: ему нужны файлы сертификата.
3. Запустите `docker compose -f compose.prod.yaml up --build -d`. Контейнер `web` выполнит миграции и `collectstatic`, затем запустит Gunicorn. Nginx отдаёт `/static/`, пропускает HTTP-запросы к ACME challenge и перенаправляет остальной HTTP на HTTPS.
4. Настройте ежедневное продление по инструкции ниже. Проверьте `docker compose -f compose.prod.yaml logs web nginx` и `docker compose -f compose.prod.yaml exec web python manage.py check --deploy`. Два предупреждения HSTS описаны ниже.

### Первый выпуск сертификата

Выполняйте команды из корня проекта на сервере. Замените `example.com`, `www.example.com` и `admin@example.com` на свои домены и почту. У каждого указанного домена должны быть корректные DNS-записи, а порт 80 должен быть доступен из Интернета и вести на этот Nginx. Для первого выпуска порт 80 должен быть свободен: если там уже работает прежний Nginx, остановите его перед запуском временного сервиса. Не запускайте основной `nginx` до получения сертификата.

```sh
docker compose -f compose.prod.yaml --profile bootstrap up -d nginx-bootstrap
docker compose -f compose.prod.yaml run --rm certbot certonly --webroot -w /var/www/certbot --non-interactive --agree-tos --email admin@example.com --cert-name empire -d example.com -d www.example.com
docker compose -f compose.prod.yaml --profile bootstrap stop nginx-bootstrap
docker compose -f compose.prod.yaml up --build -d
```

Если сертификат нужен только для одного домена, удалите второй аргумент `-d`. Имя сертификата `empire` должно остаться: основной Nginx читает `/etc/letsencrypt/live/empire/fullchain.pem` и `privkey.pem`. Файлы Certbot хранятся в исключённом из Git каталоге `deploy/letsencrypt/`. Каталог `deploy/acme/` общий для Certbot и Nginx. При ошибке выпуска оставьте `nginx-bootstrap` запущенным, исправьте DNS или доступ к порту 80 и повторите команду Certbot.

### Автоматическое продление

После запуска основного Nginx откройте crontab командой `sudo crontab -e` и добавьте ежедневный запуск скрипта (вместо `/absolute/path/to/project` укажите абсолютный путь к проекту). Убедитесь, что служба cron запущена:

```cron
17 3 * * * /absolute/path/to/project/deploy/renew-certificate.sh >> /var/log/empire-certbot.log 2>&1
```

Скрипт запускает `certbot renew` в Compose и после успешного завершения перезагружает основной Nginx, чтобы он прочитал обновлённый сертификат. Nginx перезагружается и в дни, когда сертификат ещё не нуждается в продлении. Проверьте тестовое продление после настройки cron:

```sh
docker compose -f compose.prod.yaml run --rm certbot renew --dry-run
```

Успешный `--dry-run` проверяет выпуск через тестовый сервер Let's Encrypt; его нужно выполнить на сервере с рабочими DNS и портом 80. После изменения списка доменов перевыпустите сертификат с тем же `--cert-name empire` и перезагрузите Nginx.

SQLite хранится в томе `database`, статика — в томе `staticfiles`. `docker compose -f compose.prod.yaml down` не удаляет их и каталоги `deploy/letsencrypt/` и `deploy/acme/`; не используйте `down -v`, если нужно сохранить заявки. Если переносите существующую базу, отдельно перенесите её в том до приёма заявок. Порт Gunicorn наружу не опубликован. Запускайте dev и production в разных каталогах или задайте разные Compose project names, чтобы не смешивать сервисы.

## Менеджеры заявок

После миграций в админке появляется группа «Менеджеры заявок» с правами просмотра и изменения заявок. Суперпользователь создаёт каждому менеджеру отдельного пользователя с доступом к админке (`is_staff`) и добавляет его в эту группу. Менеджер может менять статус и комментарий; при переводе незакреплённой заявки в работу он автоматически становится ответственным. Группе не выдаются права удаления заявок и управления настройками сайта.

## Запуск без Docker

1. Установите зависимости: `python -m pip install -r requirements.txt`. Для локальной разработки используйте `requirements-dev.txt`.
2. Задайте переменные окружения из `.env.example` с реальным доменом и собственным секретом. Файл `.env.example` — только образец; Django не читает `.env` автоматически. Секрет можно получить командой `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. Не добавляйте секрет в Git.
3. Выполните `python manage.py check --deploy`, `python manage.py migrate` и `python manage.py collectstatic --noinput` в том же окружении.
4. Запустите `gunicorn mantage_empire.wsgi:application --bind 127.0.0.1:8000 --workers 2` под менеджером процессов (например, systemd). Не открывайте порт 8000 наружу: Django доверяет заголовку `X-Forwarded-Proto` от локального Nginx.
5. Настройте Nginx по `nginx.conf.example`, заменив домен, пути к сертификату и `/srv/mantage-empire/staticfiles/` на фактический `STATIC_ROOT`. Получите действительный TLS-сертификат и перезагрузите Nginx.

Начальное HSTS — 1 час. Увеличивайте его только после проверки HTTPS на всех используемых доменах. SQLite требует резервного копирования и подходит для одного небольшого экземпляра; при росте нагрузки настройте отдельную СУБД. В production Nginx ограничивает `/api/tickets/` по IP: средняя скорость 6 запросов в минуту с кратким всплеском до 2 дополнительных запросов; превышение возвращает 429. Это правило общее для обоих Gunicorn workers. В dev без Nginx ограничение не действует. Если перед Nginx появится CDN или ещё один прокси, настройте доверенный real IP на Nginx, иначе лимит будет общим для адреса этого прокси.

`check --deploy` пока оставляет W005 и W021: включение HSTS для всех поддоменов и preload требует отдельного решения о реальных доменах и постоянной HTTPS-доступности. Не включайте эти параметры только ради пустого вывода проверки.
