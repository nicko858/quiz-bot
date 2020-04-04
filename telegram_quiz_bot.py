import telegram
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    RegexHandler,
    ConversationHandler,
    )
import logging
from os import getenv
from os import access
from os import path
from os import R_OK
from dotenv import load_dotenv
import re
import random
import redis
from textwrap import dedent
import argparse
from argparse import ArgumentTypeError

NEW_QUESTION, ANSWER = range(2)

SUCCESS_MESSAGE = '''\
    Правильно! Поздравляю!
    Для следующего вопроса нажми «Новый вопрос»
    '''

FAIL_MESSAGE = 'Неправильно... Попробуешь ещё раз?'

SURRENDER_MESSAGE = '''\
    Вот тебе правильный ответ: {0}\n
    Чтобы продолжить, нажми «Новый вопрос»
    '''


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


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


def set_quiz_bot_logging(log_level, bot_token, chat_id):
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


def connect_to_quiz_db(db_host, db_port, db_passwd):
    quiz_db = redis.Redis(
        host=db_host,
        password=db_passwd,
        port=db_port,
        db=0,
        decode_responses=True,
        )
    return quiz_db


def handle_new_question_request(bot, update):
    user = update.message.chat.username
    question = random.choice(list(quiz_data.keys()))
    response = question
    quiz_db.set(user, question)
    update.message.reply_text(text=response)
    return ANSWER


def handle_solution_attempt(bot, update):
    user = update.message.chat.username
    question = quiz_db.get(user)
    if is_answer_correct(update.message.text, question):
        response = dedent(SUCCESS_MESSAGE)
        state = NEW_QUESTION
    else:
        response = FAIL_MESSAGE
        state = ANSWER
    update.message.reply_text(text=response)
    return state


def handle_surrender(bot, update):
    user = update.message.chat.username
    question = quiz_db.get(user)
    answer = quiz_data[question]
    response = dedent(SURRENDER_MESSAGE.format(answer))
    update.message.reply_text(text=response)
    return NEW_QUESTION


def is_answer_correct(answer, question):
    answer_body, *_ = re.split(r'\.|\(', answer)
    return answer_body.lower() in quiz_data[question].lower()


def start(bot, update):
    custom_keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = telegram.ReplyKeyboardMarkup(
        custom_keyboard
        )
    update.message.reply_text(
        'Привет! Я бот для викторин! Чтобы продолжить, нажми «Новый вопрос»',
        reply_markup=reply_markup
        )
    return NEW_QUESTION


def stop(bot, update):
    update.message.reply_text(
        'Спасибо за участие в викторине!',
        reply_markup=telegram.ReplyKeyboardRemove()
        )
    return ConversationHandler.END


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


if __name__ == '__main__':
    load_dotenv()
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
    updater = Updater(telebot_token)
    logger = set_quiz_bot_logging('info', telebot_token, logger_chat_id)
    logger.info('Bot {0} has started!'.format(__file__))
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            ],
        states={
            NEW_QUESTION: [
                RegexHandler('^Новый вопрос', handle_new_question_request)
                ],
            ANSWER: [
                RegexHandler('^Сдаться', handle_surrender),
                MessageHandler(Filters.text, handle_solution_attempt)
                ],
        },
        fallbacks=[CommandHandler('stop', stop)],
    )
    dp.add_handler(conv_handler)
    updater.start_polling()
