import json
import logging
import re
from datetime import datetime

import pytz
from faunadb import query as q
from faunadb.client import FaunaClient
from faunadb.objects import Ref
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

from libgen import fetch_link, find_page

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%d-%b-%y %H:%M:%S",
)
logger = logging.getLogger(__name__)


config = json.load(open("config.json"))
client = FaunaClient(secret=config["db"]["secret"])
indexes = client.query(q.paginate(q.indexes()))


def start(update, context):
    name = update.message.chat.first_name
    chat_id = update.effective_chat.id
    details = client.query(q.exists(q.match(q.index("id"), chat_id)))
    if not details:
        client.query(
            q.create(
                q.collection("users"),
                {
                    "data": {
                        "id": chat_id,
                        "name": name,
                        "last_command": "",
                        "date": datetime.now(pytz.UTC),
                    },
                },
            )
        )
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["start"].format(name)
    )
    button = [
        [KeyboardButton("/search"), KeyboardButton("/help")],
        [KeyboardButton("/contribute")],
    ]
    reply_markup = ReplyKeyboardMarkup(button, resize_keyboard=True)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["menu"],
        reply_markup=reply_markup,
    )
    user = client.query(q.get(q.match(q.index("id"), chat_id)))
    client.query(
        q.update(
            q.ref(q.collection("users"), user["ref"].id()),
            {"data": {"last_command": ""}},
        )
    )


def search(update, context):
    chat_id = update.effective_chat.id
    user = client.query(q.get(q.match(q.index("id"), chat_id)))
    context.bot.send_message(chat_id=chat_id, text=config["messages"]["search"])
    client.query(
        q.update(
            q.ref(q.collection("users"), user["ref"].id()),
            {"data": {"last_command": "search"}},
        )
    )


def echo(update, context):
    chat_id = update.effective_chat.id
    user = client.query(q.get(q.match(q.index("id"), chat_id)))
    last_command = user["data"]["last_command"]
    if last_command == "search":
        title = update.message.text
        total_books, _ = find_page(title)
        if total_books == 0:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["empty_search"]
            )
            context.bot.send_message(chat_id=chat_id, text=config["messages"]["menu"])
        else:
            button = []
            for i in range(0, total_books, 10):
                button.append(
                    [
                        InlineKeyboardButton(
                            "Search result: {} - {}".format(
                                i + 1, min(i + 10, total_books)
                            ),
                            callback_data="{}:{}".format(title, i),
                        )
                    ]
                )
            reply_markup = InlineKeyboardMarkup(button)
            context.bot.send_message(
                chat_id=chat_id,
                text="Displaying {} search results for {} 😁".format(total_books, title),
                reply_markup=reply_markup,
            )
    else:
        context.bot.send_message(chat_id=chat_id, text=config["messages"]["unknown"])

    client.query(
        q.update(
            q.ref(q.collection("users"), user["ref"].id()),
            {"data": {"last_command": ""}},
        )
    )


def button(update, context):
    chat_id = update.effective_chat.id
    query = update.callback_query
    query.answer()
    context.bot.send_message(
        chat_id=chat_id,
        text="Please wait while books are being fetched",
    )
    title = query.data.split(":")[0]
    key = int(query.data.split(":")[1])
    _, page = find_page(title)
    page = page[key : key + 10]
    for i in page:
        link, author, title = fetch_link(i["Link"])
        button = [
            [
                InlineKeyboardButton("Download", url=link),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(button)

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["search_result"].format(
                i["Title"], author, i["Size"]
            ),
            reply_markup=reply_markup,
        )


def helper(update, context):
    chat_id = update.effective_chat.id
    user = client.query(q.get(q.match(q.index("id"), chat_id)))
    context.bot.send_message(chat_id=chat_id, text=config["messages"]["help"])
    client.query(
        q.update(
            q.ref(q.collection("users"), user["ref"].id()),
            {"data": {"last_command": ""}},
        )
    )


def contribute(update, context):
    chat_id = update.effective_chat.id
    user = client.query(q.get(q.match(q.index("id"), chat_id)))
    context.bot.send_message(chat_id=chat_id, text=config["messages"]["contribute"])
    client.query(
        q.update(
            q.ref(q.collection("users"), user["ref"].id()),
            {"data": {"last_command": ""}},
        )
    )


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    updater = Updater(token=config["token"], use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler("start", start)
    helper_handler = CommandHandler("help", helper)
    contribute_handler = CommandHandler("contribute", contribute)
    search_handler = CommandHandler("search", search)
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    button_handler = CallbackQueryHandler(button)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(helper_handler)
    dispatcher.add_handler(contribute_handler)
    dispatcher.add_handler(search_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(button_handler)
    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
