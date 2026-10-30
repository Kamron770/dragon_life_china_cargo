"""Starts the Telegram bot, the operator web panel and the Google Sheets backup together."""
import asyncio
import hashlib
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from app import sheets
from app.bot.handlers import router
from app.config import settings
from app.db import init_db
from app.services import set_bot
from app.web.main import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dragonlife")

WEBHOOK_PATH = "/tg/webhook"
WEBHOOK_SECRET = hashlib.sha256(f"tg:{settings.SECRET_KEY}".encode()).hexdigest()[:48]


def add_webhook_route(app: FastAPI, bot: Bot, dp: Dispatcher) -> None:
    @app.post(WEBHOOK_PATH, include_in_schema=False)
    async def telegram_webhook(request: Request):
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
            return PlainTextResponse("forbidden", status_code=403)
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await dp.feed_update(bot, update)
        return PlainTextResponse("ok")


async def main() -> None:
    await init_db()

    app = create_app()
    bot = dp = None
    if settings.BOT_TOKEN:
        bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
    else:
        log.warning("BOT_TOKEN is not set — only the web panel is running")
    set_bot(bot)

    use_webhook = bool(bot and settings.WEBHOOK_BASE)
    if use_webhook:
        add_webhook_route(app, bot, dp)

    server = uvicorn.Server(uvicorn.Config(app, host=settings.WEB_HOST, port=settings.WEB_PORT,
                                           proxy_headers=True, forwarded_allow_ips="*"))
    tasks = [asyncio.create_task(sheets.sync_loop())]
    if use_webhook:
        url = settings.WEBHOOK_BASE + WEBHOOK_PATH
        await bot.set_webhook(url, secret_token=WEBHOOK_SECRET,
                              allowed_updates=dp.resolve_used_update_types())
        log.info("Bot webhook: %s", url)
    elif bot:
        await bot.delete_webhook()  # polling does not work while a webhook is set
        tasks.append(asyncio.create_task(dp.start_polling(bot, handle_signals=False)))
        log.info("Bot: long polling")
    log.info("Web panel: http://%s:%s", settings.WEB_HOST, settings.WEB_PORT)
    try:
        await server.serve()
    finally:
        if bot and not use_webhook:
            await dp.stop_polling()
        for task in tasks:
            task.cancel()
        if bot:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
