"""aiogram-бот: вход в Mini App.

Роль бота по стратегии — «рычаг», который запускает приложение и приводит
студента к одной сессии. Сама визуализация (свободные часы, лента, ценность,
ТМ-карточки) живёт в Mini App; бот даёт точку входа и приветствие (F1).
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("curator-bot")

dp = Dispatcher()

WELCOME = (
    "<b>Школа кураторов</b> 👋\n\n"
    "Этот бот помогает за одну сессию научиться самому ориентироваться во "
    "внеучебке Академии. Внутри ты увидишь:\n\n"
    "🕒 <b>Свои свободные часы</b> на неделю и защищённый внеучебный час\n"
    "🎯 <b>Ленту мероприятий</b> по твоим интересам\n"
    "💡 <b>Ценность</b> каждого события: навык, баллы, портфолио\n"
    "⚠️ <b>Подсветку пересечений</b> при записи\n"
    "🧭 <b>Тайм-менеджмент</b>: 3 горизонта и учебные цели\n\n"
    "Нажми кнопку ниже, чтобы открыть приложение."
)

HELP = (
    "Я провожу тебя во внеучебку ЭМИТ.\n\n"
    "• /start — открыть приложение\n"
    "• Кнопка «Открыть» рядом с полем ввода тоже запускает Mini App.\n\n"
    "Если кнопка не открывается — приложение должно быть размещено по HTTPS "
    "(переменная WEBAPP_URL)."
)


def _is_https(url: str) -> bool:
    return url.lower().startswith("https://")


def _webapp_url(screen: str | None = None) -> str:
    url = settings.webapp_url
    if screen:
        url += ("&" if "?" in url else "?") + "screen=" + screen
    return url


def _webapp_kb(
    text: str = "🚀 Открыть приложение", screen: str | None = None
) -> InlineKeyboardMarkup | None:
    if not _is_https(settings.webapp_url):
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=_webapp_url(screen)))]
        ]
    )


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    kb = _webapp_kb()
    if kb is None:
        await message.answer(
            WELCOME
            + f"\n\nСсылка на приложение: {settings.webapp_url}\n"
            "<i>(для кнопки-виджета нужен HTTPS-адрес)</i>"
        )
    else:
        await message.answer(WELCOME, reply_markup=kb)


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP)


@dp.message(Command("organizer"))
async def cmd_organizer(message: Message) -> None:
    kb = _webapp_kb("📣 Открыть кабинет организатора", screen="organizer")
    if kb is None:
        await message.answer(f"Кабинет организатора: {_webapp_url('organizer')}")
    else:
        await message.answer(
            "<b>Кабинет организатора</b>\nДобавляй и редактируй свои мероприятия.",
            reply_markup=kb,
        )


@dp.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    kb = _webapp_kb("🛠️ Открыть админку", screen="admin")
    if kb is None:
        await message.answer(f"Админка: {_webapp_url('admin')}")
    else:
        await message.answer(
            "<b>Админка</b>\nРасписание, справочники, модерация и роли.\n"
            "<i>Доступ — только у администраторов.</i>",
            reply_markup=kb,
        )


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN не задан. Укажи токен от @BotFather в .env"
        )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Кнопка-меню «Открыть» рядом с полем ввода (только для HTTPS).
    if _is_https(settings.webapp_url):
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Открыть",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось установить menu button: %s", exc)

    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Открыть приложение"),
                BotCommand(command="organizer", description="Кабинет организатора"),
                BotCommand(command="admin", description="Админка"),
                BotCommand(command="help", description="Помощь"),
            ]
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось установить команды: %s", exc)

    logger.info("Бот запущен (polling). WEBAPP_URL=%s", settings.webapp_url)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
