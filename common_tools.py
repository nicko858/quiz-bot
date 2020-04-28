import redis
from os import access
from os import path
from os import R_OK
from argparse import ArgumentTypeError
import argparse
import re


def check_file_path(file_path):
    read_ok = access(path.dirname(file_path), R_OK)
    error_msg = "Access error or directory {0} doesn't exist!"
    if not read_ok:
        raise ArgumentTypeError(error_msg.format(file_path))
    elif path.isdir(file_path):
        raise ArgumentTypeError("The '{0}' is not a file!".format(file_path))
    return file_path


def connect_to_quiz_db(db_host, db_port, db_passwd):
    quiz_db = redis.Redis(
        host=db_host,
        password=db_passwd,
        port=db_port,
        db=0,
        decode_responses=True,
        )
    return quiz_db


def read_quiz_file(file_path):
    with open(file_path, 'r', encoding='KOI8-R') as file_handler:
        content = file_handler.read().split('\n\n')
    return content


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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('quiz_file_path', type=check_file_path)
    return parser.parse_args()


def is_answer_correct(answer, question, quiz_data):
    answer_body, *_ = re.split(r'\.|\(', answer)
    return answer_body.lower() in quiz_data[question].lower()


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
