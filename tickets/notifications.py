import asyncio
import json
from urllib.request import Request, urlopen

from django.core.mail import send_mail
from maxo import Bot


def message_for(ticket):
    return f"Новая заявка #{ticket.pk}\nИмя: {ticket.name}\nТелефон: {ticket.phone}"


def backlog_message(count):
    return f"За время простоя накопилось {count} заявок. Проверьте новые заявки в админке сайта."


def send_email(recipient, text):
    if send_mail("Новые заявки с сайта", text, None, [recipient], fail_silently=False) != 1:
        raise RuntimeError("Почтовый сервер не подтвердил отправку")


def send_telegram(token, chat_id, text):
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram не подтвердил доставку")


async def _send_max(token, chat_id, text):
    async with Bot(token, warming_up=False) as bot:
        await bot.send_message(chat_id=int(chat_id), text=text)


def send_max(token, chat_id, text):
    asyncio.run(asyncio.wait_for(_send_max(token, chat_id, text), timeout=8))
