# Развёртывание на Linux

## Docker Compose: локальная разработка

Запустите `docker compose up --build`. Откройте `http://localhost:8000/`. Сертификат и `.env` не нужны: используется `runserver`, `DEBUG=true` и `django-browser-reload`. Код подключён как локальная папка, поэтому изменения видны в контейнере. База хранится в отдельном томе `dev_database`.

## Docker Compose: production

1. Скопируйте `.env.example` в `.env`, задайте реальный домен и случайный `DJANGO_SECRET_KEY` (команда для генерации ниже). `.env` исключён из Git.
   Укажите канонический адрес главной в `DJANGO_PUBLIC_SITE_URL` (например, `https://example.com`), чтобы включить canonical и Open Graph метаданные и использовать этот адрес в `robots.txt` и `sitemap.xml`.
2. Положите сертификат и ключ для домена в `deploy/certs/fullchain.pem` и `deploy/certs/privkey.pem`. Каталог исключён из Git. Сертификат нужно получать и обновлять отдельно; Compose сам этого не делает.
3. Запустите `docker compose -f compose.prod.yaml up --build -d`. Контейнер `web` выполнит миграции и `collectstatic`, затем запустит Gunicorn. Nginx отдаёт `/static/` и перенаправляет HTTP на HTTPS.
4. Проверьте `docker compose -f compose.prod.yaml logs web nginx` и `docker compose -f compose.prod.yaml exec web python manage.py check --deploy`. Два предупреждения HSTS описаны ниже.

SQLite хранится в томе `database`, статика — в томе `staticfiles`. `docker compose -f compose.prod.yaml down` не удаляет их; не используйте `down -v`, если нужно сохранить заявки. Если переносите существующую базу, отдельно перенесите её в том до приёма заявок. Порт Gunicorn наружу не опубликован. Запускайте dev и production в разных каталогах или задайте разные Compose project names, чтобы не смешивать сервисы.

## Запуск без Docker

1. Установите зависимости: `python -m pip install -r requirements.txt`. Для локальной разработки используйте `requirements-dev.txt`.
2. Задайте переменные окружения из `.env.example` с реальным доменом и собственным секретом. Файл `.env.example` — только образец; Django не читает `.env` автоматически. Секрет можно получить командой `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. Не добавляйте секрет в Git.
3. Выполните `python manage.py check --deploy`, `python manage.py migrate` и `python manage.py collectstatic --noinput` в том же окружении.
4. Запустите `gunicorn mantage_empire.wsgi:application --bind 127.0.0.1:8000 --workers 2` под менеджером процессов (например, systemd). Не открывайте порт 8000 наружу: Django доверяет заголовку `X-Forwarded-Proto` от локального Nginx.
5. Настройте Nginx по `nginx.conf.example`, заменив домен, пути к сертификату и `/srv/mantage-empire/staticfiles/` на фактический `STATIC_ROOT`. Получите действительный TLS-сертификат и перезагрузите Nginx.

Начальное HSTS — 1 час. Увеличивайте его только после проверки HTTPS на всех используемых доменах. SQLite требует резервного копирования и подходит для одного небольшого экземпляра; при росте нагрузки настройте отдельную СУБД. В production Nginx ограничивает `/api/tickets/` по IP: средняя скорость 6 запросов в минуту с кратким всплеском до 2 дополнительных запросов; превышение возвращает 429. Это правило общее для обоих Gunicorn workers. В dev без Nginx ограничение не действует. Если перед Nginx появится CDN или ещё один прокси, настройте доверенный real IP на Nginx, иначе лимит будет общим для адреса этого прокси.

`check --deploy` пока оставляет W005 и W021: включение HSTS для всех поддоменов и preload требует отдельного решения о реальных доменах и постоянной HTTPS-доступности. Не включайте эти параметры только ради пустого вывода проверки.
