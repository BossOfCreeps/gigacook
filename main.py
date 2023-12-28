import logging
from os import environ

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonCommands, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler
from telegram.ext.filters import COMMAND, TEXT

from db import Bookmark, Product, Stage, run_async_session
from gpt import gpt_call

load_dotenv()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


product_create_button = [[InlineKeyboardButton("Добавить ещё", callback_data="product_create")]]


async def command_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = [
        ("start", "Начало"),
        ("products", "Товары"),
        ("recipe", "Получить рецепт"),
        ("bookmarks", "Закладки с рецептами"),
    ]

    await Stage.set(user=update.effective_user.id, name="start")

    await update.effective_user.get_bot().set_my_commands([BotCommand(c, d) for c, d in commands])
    await update.effective_user.set_menu_button(MenuButtonCommands())

    await update.message.reply_html(
        "Данный бот запоминает товары и генерирует рецепт по ним.\n"
        f"Список команд:\n"
        f"{'\n'.join([f'/{c} - {d}' for c, d in commands])}"
    )


async def command_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await Stage.set(user=update.effective_user.id, name="product_list")

    buttons = [
        [InlineKeyboardButton(f"{product.name} [удалить]", callback_data=f"product_delete {product.id}")]
        for product in await Product.read(update.effective_user.id)
    ] + product_create_button

    await update.effective_user.send_message("Текущие продукты:", reply_markup=InlineKeyboardMarkup(buttons))


async def command_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await Stage.set(user=update.effective_user.id, name="recipe")

    products = await Product.read(update.effective_user.id)
    if len(products) == 0:
        await update.effective_user.send_message("У вас нет товаров")

    payload = f"Напиши рецепт одного блюда используя только " f"{', '.join([p.name for p in products])}"

    await update.effective_user.send_message(
        gpt_call(payload),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Сохранить", callback_data="bookmark_create")]]),
    )


async def command_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await Stage.set(user=update.effective_user.id, name="bookmark_list")

    for bookmark in await Bookmark.read(update.effective_user.id):
        await update.effective_user.send_message(
            bookmark.text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("удалить", callback_data=f"bookmarks_delete {bookmark.id}")]]
            ),
        )
    else:
        await update.effective_user.send_message("Закладок нет")


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    stage = (await Stage.read(update.effective_user.id))[0].name

    if stage == "product_create":
        await Product.create(user=update.effective_user.id, name=text)
        await command_products(update, context)
    else:
        await update.effective_user.send_message("Сообщение не распознано")


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    arr = update.callback_query.data.split()
    data, pk = arr[0], int(arr[1]) if len(arr) == 2 else None

    await Stage.set(user=update.effective_user.id, name=data)

    if data == "product_create":
        await update.effective_user.send_message("Введите название продукта")

    elif data == "product_delete":
        await Product.delete(pk)
        await update.effective_user.send_message("Продукт удалён")
        await command_products(update, context)

    elif data == "bookmark_create":
        await Bookmark.create(user=update.effective_user.id, text=update.callback_query.message.text)
        await update.effective_user.send_message("Рецепт сохранён в закладки")

    elif data == "bookmarks_delete":
        await Bookmark.delete(pk)
        await update.effective_user.send_message("Продукт удалён")
        await command_bookmarks(update, context)


def run_polling_tg_app():
    application = Application.builder().token(environ["TELEGRAM_TOKEN"]).build()

    application.add_handler(CommandHandler("start", command_start))
    application.add_handler(CommandHandler("products", command_products))
    application.add_handler(CommandHandler("recipe", command_recipe))
    application.add_handler(CommandHandler("bookmarks", command_bookmarks))

    application.add_handler(MessageHandler(TEXT & ~COMMAND, message))

    application.add_handler(CallbackQueryHandler(button))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_async_session()

    run_polling_tg_app()
