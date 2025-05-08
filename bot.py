#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Tic tac toe game on telegram
# This program is dedicated to the public domain under the CC0 license.
from uuid import uuid4

import sys
from os import environ

from pymongo.mongo_client import MongoClient

from telegram import InlineQueryResultArticle,  \
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ApplicationBuilder, InlineQueryHandler, CommandHandler, \
    CallbackQueryHandler, ChosenInlineResultHandler, CallbackContext
import logging

import game
from game import Game
from emoji import Emoji



env = environ.copy()

# for some checking on go tests
TEST = True

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)

logger = logging.getLogger(__name__)

murl = env.get('MONGO', 'mongo:27017')

client = MongoClient('mongodb://' + murl)

db = client.tictactoe


def clear():
    db.games.remove({})

# clear()


def create_new_game(bot, update):
    game = Game(bot, update)
    result = db.games.insert_one(game.to_json())

    if TEST:
        results = db.games.find({"_id": result})
        logger.debug('AFter creating Heuston we found %s in db', str(results))


def find_game(game_id, bot, update):

    result = db.games.find_one({"game_id": game_id})

    if TEST:
        logger.debug(
            'While searching for game with id %s we found: %s',
            game_id, str(result))

    if result is None:
        return None
    else:
        game = Game(bot, update, result)
        return game


def update_game(game):

    result = db.games.find_one_and_replace(
        {"game_id": game.id},
        game.to_json())

    if TEST:
        logger.debug('after update we get %s', str(result))


def get_games_in_progress_count():

    count = db.games.count_documents({'status': {'$lte': game.WAITING_FOR_PLAYER}})
    return count


def get_games_count():
    count = db.games.count_documents({})
    return count


def get_playing_users_count():
    x_p = filter(lambda x: 'player_id' in x, db.games.distinct('player_x'))
    o_p = filter(lambda y: 'player_id' in y, db.games.distinct('player_0'))
    x_players = set(map(lambda g: g['player_id'], x_p))
    o_players = set(map(lambda g: g['player_id'], o_p))
    return len(x_players | o_players)


async def start_or_help(update: Update, context: CallbackContext):
    await context.bot.sendMessage(update.message.chat_id, text='Hi! \nType @tictoetac_bot in any chat and select the game you want to play.' )


async def status(update: Update, context: CallbackContext):

    await context.bot.sendMessage(
        update.message.chat_id,
        text=str(get_games_in_progress_count()) +
        ' games running now.\nTotal number of games - ' +
        str(get_games_count()) +
        '.\n' + str(get_playing_users_count()) + ' players.')


def get_initial_keyboard():

    player_x = InlineKeyboardButton(
        'Play for ' + Emoji.HEAVY_MULTIPLICATION_X,
        callback_data='player_x')
    player_o = InlineKeyboardButton(
        'Play for ' + Emoji.HEAVY_LARGE_CIRCLE,
        callback_data='player_o')
    return InlineKeyboardMarkup([[player_x], [player_o]])


def is_callback_valid(callback_data):
    """Checking callback validity"""

    if (callback_data == 'player_x') or (callback_data == 'player_o'):
        return True

    if (len(callback_data) == 1) and (callback_data.isdigit()) and \
       (callback_data != '9'):
        return True

    return False


async def chose_inline_result(update: Update, context: CallbackContext):

    logger.info("creating game")
    create_new_game(context.bot, update)



async def rate(update: Update, context: CallbackContext):

    await context.bot.sendMessage(
        update.message.chat_id,
        text="⭐️ If you like the bot, please [give a star](https://github.com/alikhil/tic-tac-toe-telegram-bot/). ⭐️",
        parse_mode="Markdown")


async def inline_query_callback(update: Update, context: CallbackContext):
    results = list()

    results.append(InlineQueryResultArticle(
        id=uuid4(),
        title='Create Tic-Tac-Toe 3x3 round.',
        input_message_content=InputTextMessageContent('Tic-Tac-Toe round created!'),
        reply_markup=get_initial_keyboard()))

    await context. bot.answerInlineQuery(update.inline_query.id, results=results)


def error(update: Update, context: CallbackContext):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


async def handle_inline_callback(update: Update, context: CallbackContext):
    logger.debug('handle a inline callback' + str(update))
    query = update.callback_query
    text = query.data
    game_id = update.callback_query.inline_message_id

    game_ = find_game(game_id, context.bot, update)
    # logger.debug('query: ' + json.dumps(query.__dict__))
    # logger.info('text: ' + text)
    # logger.info('gameId: ' + game_id)
    # logger.info('game_ is None: ' + str(game_ is None))

    if (game_ is not None) and (is_callback_valid(text)):
        await game_.handle(text, update)
        update_game(game_)
    else:
        await context.bot.answerCallbackQuery(query.id, text="Game does not exist :(( !")


def main():
    # Create the Updater and pass it your bot's token.
    logger.info('Bot started')
    test = "YOUR_BOT_TOKEN"
    token = env["TOKEN"] if "TOKEN" in env else test
    app = ApplicationBuilder().token(token).build()
    # on different commands - answer in Telegram
    app.add_handler(CommandHandler("start", start_or_help))
    app.add_handler(CommandHandler("help", start_or_help))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(CommandHandler("rate", rate))
    # on pressing buttons from inline keyboards
    app.add_handler(CallbackQueryHandler(handle_inline_callback))
    # on noncommand i.e message - echo the message on Telegram
    app.add_handler(InlineQueryHandler(inline_query_callback))
    # on creating game
    app.add_handler(ChosenInlineResultHandler(chose_inline_result))
    # log all errors
    app.add_error_handler(error)

    # Start the Bot
    app.run_polling()

if __name__ == '__main__':
    main()
