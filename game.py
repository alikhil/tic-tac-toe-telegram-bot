import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from emoji import Emoji

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger('Game')
# game status constants
WAITING_FOR_START, WAITING_FOR_PLAYER, COMPLETED, FINISHED = range(0, 4)

STATUSES = ['Waiting for start.',
            'Game is running.',
            'Game is finished!',
            'Game is finished!']

EMPTY = ' '
EMPTY_CELL, CELL_X, CELL_O = range(3)


def make_button(button):

        emoji = 'ERROR'
        if button[1] == EMPTY_CELL:
            emoji = EMPTY

        if button[1] == CELL_X:
            emoji = Emoji.HEAVY_MULTIPLICATION_X

        if button[1] == CELL_O:
            emoji = Emoji.HEAVY_LARGE_CIRCLE

        return InlineKeyboardButton(emoji, callback_data=str(button[0]))


class Game:
    """Entity for game"""

    def __init__(self, bot, update, json=None):

        self.bot = bot
        if json is not None:
            self.id = json['game_id']
            self.status = int(json['status'])
            self.players_count = int(json['players_count'])
            self.step = int(json['step'])
            self.map_ = [int(cell) for cell in json['map_']]

            if json['player_x']:
                self.player_x = Player(update, json['player_x'])
            else:
                self.player_x = None

            if json['player_o']:
                self.player_o = Player(update, json['player_o'])
            else:
                self.player_o = None

            if json['winner']:
                self.winner = Player(update, json['winner'])
            else:
                self.winner = None

            return

        self.id = update.chosen_inline_result.inline_message_id
        self.status = WAITING_FOR_START
        self.players_count = 0
        self.player_o = None
        self.player_x = None
        self.winner = None
        self.map_ = [0] * 9
        self.step = 0
        self.notified = False

    def handle(self, command, update):
        # update - callback query update
        query_id = update.callback_query.id

        logger.info('Handled command ' + command)

        if self.status == WAITING_FOR_START:

            if (command == 'player_x') and (self.find_player(update) is None):

                self.chose_player(0, update)
            elif ((command == 'player_o') and
                  (self.find_player(update) is None)):

                self.chose_player(1, update)

            else:
                self.show_message(query_id, 'You are already playing!')

        elif self.status == WAITING_FOR_PLAYER:

            if command.isdigit():

                player = self.find_player(update)

                if player == self.get_current_player():

                    self.try_to_make_step(command, update)

                else:
                    self.show_message(query_id, 'Hey, it is not your turn!')

            elif command == 'notify':

                if not self.notified:
                    self.bot.reply_text(
                        reply_to_message_id=self.id,
                        text=self.get_current_player().username +
                        'make your step.')

            else:
                self.show_message(query_id, 'What are you trying to do?')

        elif self.status == FINISHED or self.status == COMPLETED:

            self.show_message(query_id, 'Game is finished!')

    def chose_player(self, id, update):

        query_id = update.callback_query.id
        inline_message_id = update.callback_query.inline_message_id
        if id == 0:

            if self.player_x is None:

                self.player_x = Player(update)
                self.players_count += 1
                self.show_message(
                    query_id,
                    'Now you are playing for ' + Emoji.HEAVY_MULTIPLICATION_X)

            else:
                self.show_message(
                    query_id,
                    'There is somebody who already plays for ' +
                    Emoji.HEAVY_MULTIPLICATION_X)

        elif id == 1:

            if self.player_o is None:

                self.player_o = Player(update)
                self.players_count += 1
                self.show_message(
                    query_id,
                    'Now you are playing for ' +
                    Emoji.HEAVY_LARGE_CIRCLE)

            else:
                self.show_message(
                    query_id,
                    'There is somebody who already plays for ' +
                    Emoji.HEAVY_LARGE_CIRCLE)

        if self.players_count == 2:

            self.status = WAITING_FOR_PLAYER
            self.set_message(
                inline_message_id,
                self.get_game_status(),
                self.get_map())

        elif self.players_count == 1:

            player = None
            if self.player_x is None:

                player = InlineKeyboardButton(
                    'Play for ' + Emoji.HEAVY_MULTIPLICATION_X,
                    callback_data='player_x')
            else:

                player = InlineKeyboardButton(
                    'Play for ' + Emoji.HEAVY_LARGE_CIRCLE,
                    callback_data='player_o')

            keyboard = InlineKeyboardMarkup([[player]])

            self.set_keyboard(inline_message_id, keyboard)

    def set_keyboard(self, inline_message_id, keyboard):

        self.bot.editMessageReplyMarkup(reply_markup=keyboard,
                                        inline_message_id=inline_message_id)

    def is_completed(self, cell):

        it = iter(self.map_)
        board = list(zip(it, it, it))
        x = cell // 3
        y = cell % 3

        logger.info(board)
        # check if previous move caused a win on vertical line
        if board[0][y] == board[1][y] == board[2][y]:
            return True

        # check if previous move caused a win on horizontal line
        if board[x][0] == board[x][1] == board[x][2]:
            return True

        # check if previous move was on the main diagonal and caused a win
        if x == y and board[0][0] == board[1][1] == board[2][2]:
            return True

        # check if previous move was on the secondary diagonal and caused a win
        if x + y == 2 and board[0][2] == board[1][1] == board[2][0]:
            return True
        return False

    def try_to_make_step(self, cell, update):
        i = int(cell)
        if self.map_[i] == EMPTY_CELL:
            if self.get_current_player() == self.player_x:
                val = CELL_X
            else:
                val = CELL_O

            self.map_[i] = val
            self.step += 1
            # inline_message_id = update.callback_query.inline_message_id
            if self.is_completed(i):
                self.step -= 1
                self.winner = self.get_current_player()
                self.step += 1
                self.status = COMPLETED
                self.show_message(
                    update.callback_query.id, 'Congratulations! You won!')
            elif self.step == 9:
                self.status = FINISHED
                self.show_message(update.callback_query.id, 'Draw!')

            self.set_message(
                update.callback_query.inline_message_id,
                self.get_game_status(), self.get_map())

        else:
            self.show_message(
                update.callback_query.id,
                'That cell is already played! Try another one.')

    def get_current_player(self):

        if self.step % 2 == 0:
            return self.player_x

        return self.player_o

    def get_game_status(self):
        status = STATUSES[self.status]

        status += '\n'

        play_word = ' plays' if self.status <= WAITING_FOR_PLAYER else ' played'

        if self.player_x is not None:
            status += self.player_x.name + play_word + ' for ' + \
                Emoji.HEAVY_MULTIPLICATION_X + '\n'

        if self.player_o is not None:
            status += self.player_o.name + play_word + ' for ' + \
                Emoji.HEAVY_LARGE_CIRCLE + '\n'

        if self.status == WAITING_FOR_PLAYER:
            status += '\n' + self.get_current_player().name + '\'s turn. \n'

        if self.status == COMPLETED:
            status += '\n' + self.winner.name + ' won the round!'

        if self.status == FINISHED:
            status += '\n Draw!'
        return status

    def get_map(self):
        map_ = [(i, self.map_[i]) for i in range(9)]

        keyboard = InlineKeyboardMarkup(
            [list(map(make_button, map_[:3])),
                list(map(make_button, map_[3:6])),
                list(map(make_button, map_[6:9]))])

        logger.debug('inline keyboard' + str(keyboard))
        return keyboard

    def find_player(self, update):

        user_id = update.callback_query.from_user.id

        if (self.player_o is not None) and (self.player_o.id == user_id):
            return self.player_o

        if (self.player_x is not None) and (self.player_x.id == user_id):
            return self.player_x

        return None

    def show_message(self, query_id, message):

        self.bot.answerCallbackQuery(query_id, message)

    def set_message(self, message_id, message, keyboard=None):
        logger.debug('message_id:' + message_id)
        logger.info('setting message:' + message)

        self.bot.editMessageText(
            message, inline_message_id=message_id, reply_markup=keyboard)

    def to_json(self):

        return dict(
            game_id=self.id,
            status=self.status,
            players_count=self.players_count,
            map_=self.map_,
            step=self.step,
            player_x=self.json(self.player_x),
            player_o=self.json(self.player_o),
            winner=self.json(self.winner))

    def json(self, obj):
        if obj is None:
            return {}

        return obj.to_json()


class Player:
    """Player entity """

    def __init__(self, update, json=None):

        if json is not None:
            self.id = json['player_id']
            self.name = json['name']
            self.username = json['username']
            return

        from_user = update.callback_query.from_user
        self.id = from_user.id
        self.name = from_user.first_name + ' ' + from_user.last_name
        self.username = '@' + from_user.username

    def to_json(self):

        return dict(
            player_id=self.id,
            name=self.name,
            username=self.username)
