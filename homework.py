import logging
import os
import time
import requests
from dotenv import load_dotenv
import telegram
from http import HTTPStatus

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='main.log')


PRACTICUM_TOKEN = os.getenv('MY_PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('MY_TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = 6316776501

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PAYLOAD = {'from_date': 0}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

REQUEST_PARAMS = {
    'ENDPOINT': ENDPOINT,
    'HEADERS': HEADERS,
    'params': PAYLOAD
}


class WrongHttpRequestException(Exception):
    """Exception class."""

    ...


def HTTP400():
    """Exception status_code 400."""
    raise WrongHttpRequestException('В качестве параметра "from_date"'
                                    'были переданы некорректные значения')


def HTTP401():
    """Exception status_code 401."""
    raise WrongHttpRequestException('Запрос был произведён с некорректным'
                                    'или недействительным токеном')


def check_tokens():
    """Сhecking token's availability."""
    if PRACTICUM_TOKEN is None or TELEGRAM_TOKEN is None:
        return False
    else:
        return True


def send_message(bot, message):
    """Sending a message."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=f'{message}')
    except telegram.error.TelegramError:
        logging.error('Сообщение не отправлено')
    else:
        logging.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Making a request to the endpoint."""
    PAYLOAD['from_date'] = timestamp
    try:
        response = requests.get(**REQUEST_PARAMS)
        if response.status_code != HTTPStatus.OK:
            raise HTTP401()
    except requests.RequestException:
        raise HTTP400()
    response = response.json()
    return response


def check_response(response):
    """Checking the response for compliance with the documentation."""
    if not isinstance(response, dict):
        raise TypeError(f'В ответе API получен {type(response)}'
                        'вместо словаря')
    if 'homeworks' not in response or 'current_date' not in response:
        raise TypeError('Отсутсвуют ожидаемые ключи в ответе API')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Тип данных "homeworks" не "list"')
    else:
        return response['homeworks'][0]


def parse_status(homework):
    """Getting status of work."""
    status = homework['status']
    if 'homework_name' not in homework:
        raise KeyError('В ответе API не найдено название'
                       'домашней работы под ключом "homework_name"')
    else:
        homework_name = homework["homework_name"]

    if status in HOMEWORK_VERDICTS.keys():
        verdict = HOMEWORK_VERDICTS[status]
        logging.debug(f'Изменился статус работы на "{verdict}"')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise KeyError('Неожиданный статус домашней работы,'
                   'обнаруженный в ответе API.')


# Main function
def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Отсутствует обязательная переменная окружения')
        raise telegram.error.InvalidToken()

    last_message = ''

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(error)
        finally:
            if message != last_message and message is not None:
                send_message(bot, message)
            last_message = message
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
