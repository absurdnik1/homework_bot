import logging
import os
import time
import requests
from dotenv import load_dotenv
import telegram

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


def check_tokens():
    """Сhecking token's availability."""
    if PRACTICUM_TOKEN is not None and TELEGRAM_TOKEN is not None:
        return True
    else:
        logging.critical('Отсутствует обязательная переменная окружения')
        raise telegram.error.InvalidToken


def send_message(bot, message):
    """Sending a message."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=f'{message}')
        logging.debug('Сообщение отправлено')
    except telegram.error.TelegramError:
        logging.error('Сообщение не отправлено')


def get_api_answer(timestamp):
    """Making a request to the endpoint."""
    PAYLOAD['from_date'] = timestamp
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=PAYLOAD)
        if response.status_code != 200:
            logging.error
            (f'Сбой в работе программы: Эндпоинт:{ENDPOINT} недоступен')
            raise telegram.error.BadRequest
    except requests.RequestException:
        logging.error
        (f'Сбой в работе программы: Эндпоинт:{ENDPOINT} недоступен')
        raise telegram.error.BadRequest
    response = response.json()
    return response


def check_response(response):
    """Checking the response for compliance with the documentation."""
    if type(response) != dict:
        logging.error('В ответе API получен список вместо словаря')
        raise TypeError
    elif ('homeworks' in response
          and 'current_date' in response
          and type(response['homeworks']) == list):
        return response['homeworks'][0]
    else:
        logging.error('Отсутсвуют ожидаемые ключи в ответе API')
        raise TypeError


def parse_status(homework):
    """Getting status of work."""
    status = homework['status']
    if 'homework_name' in homework:
        homework_name = homework["homework_name"]
    else:
        raise KeyError('Ключ не найден')

    if status in HOMEWORK_VERDICTS.keys():
        verdict = HOMEWORK_VERDICTS[status]
        logging.debug(f'Изменился статус работы на "{verdict}"')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error('Неожиданный статус домашней работы,'
                      'обнаруженный в ответе API.')
        raise KeyError('Ключ не найден')


# Main function
def main():
    """Основная логика работы бота."""
    check_tokens()
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
        if message != last_message and message is not None:
            send_message(bot, message)
            last_message = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
