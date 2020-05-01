import vk_api
import random
from vk_api.longpoll import VkLongPoll, VkEventType
from os import getenv
from dotenv import load_dotenv
import logging
import telegram
from textwrap import dedent
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from common_tools import (
    connect_to_quiz_db,
    read_quiz_file,
    parse_quiz_data,
    parse_args,
    is_answer_correct,
)


logger = logging.getLogger(__file__)

INITIAL = 'Привет! Я бот для викторин! Чтобы продолжить, нажми «Новый вопрос»'

SUCCESS_MESSAGE = '''\
    Правильно! Поздравляю!
    Для следующего вопроса нажми «Новый вопрос»
    '''

FAIL_MESSAGE = 'Неправильно... Попробуешь ещё раз?'

NO_QUESTION = '''\
    У вас нет текущих вопросов!
    Чтобы продолжить, нажми «Новый вопрос»
    '''

SURRENDER_MESSAGE = '''\
    Вот тебе правильный ответ: {0}\n
    Чтобы продолжить, нажми «Новый вопрос»
    '''

GOODBY = 'Спасибо за участие в викторине!'


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


def set_vk_bot_logging(log_level, bot_token, chat_id):
    log_levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'error': logging.ERROR,
        'warning': logging.WARN,
    }
    tg_bot = telegram.Bot(token=bot_token)
    logger.setLevel(log_levels[log_level])
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )
    telegram_handler = TelegramLogsHandler(tg_bot, chat_id)
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)


def make_keyboard():
    keyboard = VkKeyboard()
    keyboard.add_button(
        'Новый вопрос',
        color=VkKeyboardColor.DEFAULT
        )
    keyboard.add_button(
        'Сдаться',
        color=VkKeyboardColor.DEFAULT
        )
    keyboard.add_line()
    keyboard.add_button(
        'Мой счет',
        color=VkKeyboardColor.DEFAULT
        )
    return keyboard


def handle_quiz(vk_session, vk, vk_handle_options):
    while True:
        try:
            longpoll = VkLongPoll(vk_session)
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if event.text in ("/start", "/stop"):
                        response = vk_handle_options[event.text]["response"]
                        keyboard = vk_handle_options[event.text]["keyboard"]
                        vk.messages.send(
                            user_id=event.user_id,
                            keyboard=keyboard,
                            message=response,
                            random_id=random.randint(1, 1000),
                        )
                        continue
                    elif event.text == "Новый вопрос":
                        question = random.choice(list(quiz_data.keys()))
                        response = question
                        quiz_db.set(
                            "{0}-{1}".format("vk", event.user_id),
                            question,
                            )
                    elif event.text == "Сдаться":
                        try:
                            question = quiz_db.get("{0}-{1}".format(
                                "vk",
                                event.user_id,
                                ))
                            answer = quiz_data[question]
                            quiz_db.delete("{0}-{1}".format(
                                "vk",
                                event.user_id
                                ))
                            response = dedent(SURRENDER_MESSAGE.format(answer))
                        except KeyError:
                            response = NO_QUESTION
                    else:
                        if is_answer_correct(event.text, question, quiz_data):
                            response = dedent(SUCCESS_MESSAGE)
                        else:
                            response = FAIL_MESSAGE
                    vk.messages.send(
                        user_id=event.user_id,
                        message=response,
                        random_id=random.randint(1, 1000),
                        )
        except Exception as error:
            logger.exception(error)


if __name__ == '__main__':
    load_dotenv()
    vk_token = getenv('VK_TOKEN')
    telebot_token = getenv('TELEGRAM_BOT_TOKEN')
    logger_chat_id = getenv('LOGGER_CHAT_ID')
    db_host = getenv('DB_HOST')
    db_port = getenv('DB_PORT')
    db_passwd = getenv('DB_PASSWD')
    quiz_db = connect_to_quiz_db(db_host, db_port, db_passwd)
    cli_args = parse_args()
    quiz_file_path = cli_args.quiz_file_path
    quiz_raw_data = read_quiz_file(quiz_file_path)
    quiz_data = parse_quiz_data(quiz_raw_data)
    set_vk_bot_logging('debug', telebot_token, logger_chat_id)
    logger.info('Bot {0} has started!'.format(__file__))
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()
    keyboard = make_keyboard()
    vk_handle_options = {
        "/start": {
            "response": INITIAL,
            "keyboard": keyboard.get_keyboard()
            },
        "/stop": {
            "response": GOODBY,
            "keyboard": keyboard.get_empty_keyboard()
            },
        }
    handle_quiz(vk_session, vk, vk_handle_options)
