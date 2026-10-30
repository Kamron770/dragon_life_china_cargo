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

from app.bot.handlers import router
from app.config import settings
from app.db import init_db
from app.services import BOT_STATUS, set_bot
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
        try:
            update = Update.model_validate(await request.json(), context={"bot": bot})
            await dp.feed_update(bot, update)
        except Exception as e:
            # Always answer 200: otherwise Telegram re-sends this update forever and the bot looks dead
            log.exception("Update failed: %s", e)
            BOT_STATUS["error"] = f"{type(e).__name__}: {e}"
        return PlainTextResponse("ok")


def make_bot() -> tuple[Bot | None, Dispatcher | None]:
    if not settings.BOT_TOKEN:
        BOT_STATUS["error"] = "BOT_TOKEN is empty"
        log.error("BOT_TOKEN is not set — only the web panel is running")
        return None, None
    try:
        bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    except Exception as e:  # malformed token
        BOT_STATUS["error"] = f"Bad BOT_TOKEN: {e}"
        log.error("BOT_TOKEN is invalid: %s", e)
        return None, None
    BOT_STATUS["token"] = True
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return bot, dp


async def start_bot(bot: Bot, dp: Dispatcher, use_webhook: bool) -> asyncio.Task | None:
    """Connects the bot to Telegram. Errors are logged, the web panel keeps running."""
    try:
        me = await bot.get_me()
        log.info("Bot: @%s", me.username)
        if use_webhook:
            url = settings.WEBHOOK_BASE + WEBHOOK_PATH
            await bot.set_webhook(url, secret_token=WEBHOOK_SECRET,
                                  allowed_updates=dp.resolve_used_update_types())
            BOT_STATUS.update(mode="webhook", webhook_url=url, secret=WEBHOOK_SECRET,
                              allowed_updates=dp.resolve_used_update_types())
            log.info("Bot webhook: %s", url)
            return None
        await bot.delete_webhook()  # polling does not work while a webhook is set
        BOT_STATUS["mode"] = "polling"
        log.info("Bot: long polling")
        return asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    except Exception as e:
        BOT_STATUS["error"] = f"{type(e).__name__}: {e}"
        log.exception("Bot could not connect to Telegram: %s", e)
        return None


async def main() -> None:
    await init_db()

    app = create_app()
    bot, dp = make_bot()
    set_bot(bot)
    use_webhook = bool(bot and settings.WEBHOOK_BASE)
    if use_webhook:
        add_webhook_route(app, bot, dp)

    server = uvicorn.Server(uvicorn.Config(app, host=settings.WEB_HOST, port=settings.WEB_PORT,
                                           proxy_headers=True, forwarded_allow_ips="*"))
    tasks: list[asyncio.Task] = []
    if bot:
        if polling := await start_bot(bot, dp, use_webhook):
            tasks.append(polling)
    log.info("Web panel: http://%s:%s", settings.WEB_HOST, settings.WEB_PORT)
    try:
        await server.serve()
    finally:
        if bot and BOT_STATUS["mode"] == "polling":
            await dp.stop_polling()
        for task in tasks:
            task.cancel()
        if bot:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
