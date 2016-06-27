#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Tic tac toe game on telegram
# This program is dedicated to the public domain under the CC0 license.
from uuid import uuid4

import re
import sys

from telegram import InlineQueryResultArticle, ParseMode, \
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton, Emoji
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, CallbackQueryHandler, ChosenInlineResultHandler
import logging

import game
from game import Game
from emoji import Emoji


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# keeping all games here | TODO in database
games = []

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi! Use inline query to create game.')


def help(bot, update):
    bot.sendMessage(update.message.chat_id, text='Use inline query to create game!')


def get_initial_keyboard():
    player_x = InlineKeyboardButton('Play for ' + Emoji.HEAVY_MULTIPLICATION_X, callback_data='player_x')
    player_o = InlineKeyboardButton('Play for ' + Emoji.HEAVY_LARGE_CIRCLE, callback_data=  'player_o')
    return InlineKeyboardMarkup([[player_x],[player_o]])


def is_callback_valid(callback_data):
    """Checking callback validity"""

    if (callback_data == 'player_x') or (callback_data == 'player_o'):
        return True

    if (len(callback_data) == 1) and (callback_data.isdigit()) and (callback_data != '9'):
        return True
    
    return False

def chose_inline_result(bot, update):
    global games
    games.append(Game(bot, update))

def inlinequery(bot, update):
    query = update.inline_query.query
    results = list()

    results.append(InlineQueryResultArticle(id=uuid4(),
                                            title='Create Tic-Tac-Toe round.',
                                            input_message_content=InputTextMessageContent('Tic-Tac-Toe round created!'),
                                            reply_markup=get_initial_keyboard()))

    bot.answerInlineQuery(update.inline_query.id, results=results)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def handle_callback(bot, update):
    logger.info(update)
    query = update.callback_query
    user_id = query.from_user.id
    text = query.data
    game_id = update.callback_query.inline_message_id
    # game exists
    game_ = None
    
    for i in range(len(games)):
        if games[i].id == game_id:
            game_ = games[i]
            break

    if (game_ is not None) and (is_callback_valid(text)):
        game_.handle(text, update)
        if (game_.status == game.COMPLETED) or (game_.status == game.FINISHED):
            games.remove(game_)
    else:
        bot.answerCallbackQuery(query.id, text="Game is not exist :(( !")
    

def main():
    # Create the Updater and pass it your bot's token.
    logger.info('Bot started')
    test = "203483979:AAGCq26gZcZnUbe65vzswLsRh_2lF1nqIA8"
    token = sys.argv[1] if len(sys.argv) == 2 else test
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on pressing buttons from inline keyboards
    dp.add_handler(CallbackQueryHandler(handle_callback))
    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(InlineQueryHandler(inlinequery))
    # on creating game
    dp.add_handler(ChosenInlineResultHandler(chose_inline_result))
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()