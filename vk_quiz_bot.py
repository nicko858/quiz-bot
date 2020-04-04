import vk_api
import random
from vk_api.longpoll import VkLongPoll, VkEventType
from os import getenv
from dotenv import load_dotenv
import logging
import telegram
import re
import redis
from os import access
from os import path
from os import R_OK
from textwrap import dedent
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import argparse
from argparse import ArgumentTypeError

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


def check_file_path(file_path):
    read_ok = access(path.dirname(file_path), R_OK)
    error_msg = "Access error or directory {0} doesn't exist!"
    if not read_ok:
        raise ArgumentTypeError(error_msg.format(file_path))
    elif path.isdir(file_path):
        raise ArgumentTypeError("The '{0}' is not a file!".format(file_path))
    return file_path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('quiz_file_path', type=check_file_path)
    return parser.parse_args()


def connect_to_quiz_db(db_host, db_port, db_passwd):
    quiz_db = redis.Redis(
        host=db_host,
        password=db_passwd,
        port=db_port,
        db=0,
        decode_responses=True,
        )
    return quiz_db


def is_answer_correct(answer, question):
    answer_body, *_ = re.split(r'\.|\(', answer)
    return answer_body.lower() in quiz_data[question].lower()


def read_quiz_file(file_path):
    with open(file_path, 'r', encoding='KOI8-R') as file_handler:
        content = file_handler.read().split('\n\n')
    return content


def format_record(raw_record, type='question'):
    params = {
        'question': r'Вопрос \d+:',
        'answer': r'Ответ:',
    }
    split_record = re.split(
        params[type],
        raw_record.replace('\n', ' '))
    _, formatted_record = split_record
    return formatted_record.lstrip()


def parse_quiz_data(raw_quiz_data):
    quiz_data = {}
    step_to_answer = 1
    for idx, record in enumerate(raw_quiz_data):
        if 'Вопрос' in record:
            question = format_record(record)
            raw_answer = raw_quiz_data[idx + step_to_answer]
            answer = format_record(raw_answer, type='answer')
            quiz_data[question] = answer
    return quiz_data


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
    logger = logging.getLogger(__file__)
    logger.setLevel(log_levels[log_level])
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )
    telegram_handler = TelegramLogsHandler(tg_bot, chat_id)
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)
    return logger


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


def handle_quiz(vk_session, vk):
    while True:
        try:
            longpoll = VkLongPoll(vk_session)
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    keyboard = make_keyboard()
                    if event.text == '/start':
                        response = INITIAL
                        vk.messages.send(
                            user_id=event.user_id,
                            keyboard=keyboard.get_keyboard(),
                            message=response,
                            random_id=random.randint(1, 1000),
                        )
                        continue
                    elif event.text == '/stop':
                        response = GOODBY
                        vk.messages.send(
                            user_id=event.user_id,
                            keyboard=keyboard.get_empty_keyboard(),
                            message=response,
                            random_id=random.randint(1, 1000),
                        )
                        continue
                    elif event.text == "Новый вопрос":
                        question = random.choice(list(quiz_data.keys()))
                        response = question
                        quiz_db.set(event.user_id, question)
                    elif event.text == 'Сдаться':
                        try:
                            question = quiz_db.get(event.user_id)
                            answer = quiz_data[question]
                            quiz_db.delete(event.user_id)
                            response = dedent(SURRENDER_MESSAGE.format(answer))
                        except KeyError:
                            response = NO_QUESTION
                    else:
                        if is_answer_correct(event.text, question):
                            response = dedent(SUCCESS_MESSAGE)
                        else:
                            response = FAIL_MESSAGE
                    vk.messages.send(
                        user_id=event.user_id,
                        message=response,
                        random_id=random.randint(1, 1000),
                        )
        except Exception as error:
            logger.error(error, exc_info=True)


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
    logger = set_vk_bot_logging('debug', telebot_token, logger_chat_id)
    logger.info('Bot {0} has started!'.format(__file__))
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()
    handle_quiz(vk_session, vk)