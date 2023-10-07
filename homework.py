import logging
import os
import time
import requests
import sys
import telegram
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import WrongStatusCodeException, AmbiguousException
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='main.log')


PRACTICUM_TOKEN = os.getenv('MY_PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('MY_TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_TELEGRAM_CHAT_ID')

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


def check_tokens():
    """Сhecking token's availability."""
    return all((
        PRACTICUM_TOKEN is not None,
        TELEGRAM_TOKEN is not None,
        TELEGRAM_CHAT_ID is not None
    ))


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
    REQUEST_PARAMS = {
        'ENDPOINT': ENDPOINT,
        'HEADERS': HEADERS,
        'params': PAYLOAD}
    PAYLOAD['from_date'] = timestamp
    try:
        response = requests.get(**REQUEST_PARAMS)
        if response.status_code != HTTPStatus.OK:
            raise WrongStatusCodeException(f"Статус код ответа не равен"
                                           f"{response.status_code},"
                                           "ожидаемый - {HTTPStatus.OK}."
                                           f"REQUEST_PARAMS = {REQUEST_PARAMS}"
                                           )
    except requests.RequestException:
        raise AmbiguousException(f"При обработке запроса возникло"
                                 f"неоднозначное исключение."
                                 f"REQUEST_PARAMS = {REQUEST_PARAMS}")
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
    return response['homeworks']


def parse_status(homework):
    """Getting status of work."""
    status = homework['status']
    if 'homework_name' not in homework:
        raise KeyError('В ответе API не найдено название'
                       'домашней работы под ключом "homework_name"')
    homework_name = homework["homework_name"]

    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Неожиданный статус домашней работы,'
                       'обнаруженный в ответе API.')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


# Main function
def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Отсутствует обязательная переменная окружения')
        sys.exit('Отсутствует обязательная переменная окружения')

    last_message = ''

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework == []:
                message = 'Не найдено домашних работ'
            else:
                message = parse_status(homework[0])
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(error)
        finally:
            if (
                message != last_message
                and message is not None
            ):
                send_message(bot, message)
            last_message = message
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
