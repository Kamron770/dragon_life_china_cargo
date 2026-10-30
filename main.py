"""Starts the Telegram bot, the operator web panel and the Google Sheets backup together."""
import asyncio
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app import sheets
from app.bot.handlers import router
from app.config import settings
from app.db import init_db
from app.services import set_bot
from app.web.main import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dragonlife")


async def main() -> None:
    await init_db()

    bot = dp = None
    if settings.BOT_TOKEN:
        bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
    else:
        log.warning("BOT_TOKEN is not set — only the web panel is running")
    set_bot(bot)

    server = uvicorn.Server(uvicorn.Config(create_app(), host=settings.WEB_HOST, port=settings.WEB_PORT,
                                           proxy_headers=True, forwarded_allow_ips="*"))
    tasks = [asyncio.create_task(sheets.sync_loop())]
    if dp:
        tasks.append(asyncio.create_task(dp.start_polling(bot, handle_signals=False)))
    log.info("Web panel: http://%s:%s", settings.WEB_HOST, settings.WEB_PORT)
    try:
        await server.serve()
    finally:
        if dp:
            await dp.stop_polling()
        for task in tasks:
            task.cancel()
        if bot:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
