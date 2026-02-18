import json
import logging
import pathlib
from datetime import datetime

import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

load_dotenv()

MPEI_LOGIN = os.getenv('MPEI_LOGIN')
MPEI_PASSWORD = os.getenv('MPEI_PASSWORD')

PROMETHEI_LOGIN_URL = os.getenv('PROMETHEI_LOGIN_URL')
HEADERS4LOGIN = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Sec-Ch-Ua": 'Not(A:Brand";v="8", "Chromium";v="144"',
    "Sec-Ch-Ua-Platform": "Windows",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "iframe",
    "Referer": "https://dot.mpei.ac.ru/close/auth.asp",
    "Priority": "u=0, i",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://dot.mpei.ac.ru",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}
BODY4LOGIN = {
    "ustatus": "",
    "returl": "",
    "AuthLogin": MPEI_LOGIN,
    "AuthPassword": MPEI_PASSWORD,
    "AuthRemem": 1
}


EVENTS_GETTER_URL = os.getenv('EVENTS_GETTER_URL')
HEADERS4EVENTS = {
    "Sec-Ch-Ua": 'Not(A:Brand";v="8", "Chromium";v="144"',
    "Sec-Ch-Ua-Platform": "Windows",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://dot.mpei.ac.ru/close/students/info.asp",
    "Priority": "u=1, i",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "application/xml, text/xml, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br",
}


def get_response_encoding(response: requests.Response) -> str:
    return response.text.split(' ?>')[0].split('encoding=')[-1].strip('"')


def extract_data(soup: BeautifulSoup) -> list[dict]:
    xml_fields = {"eventType", "eventDateBegin", "eventDateEnd", "courseName", "elementName"}
    event_type_being_collected = "event"        # if eventType==event : item will be collected
    
    data = []
    for item in soup.find_all('item'):
        if item.find("eventType").text == event_type_being_collected:
            event = {}
            for field in xml_fields:
                event[field] = item.find(field).text
            data.append(event)
    
    return data        


def get_auth_cookie() -> dict:
    """
    Returns:
        dict: auth cookies
    """
    logger.info('requesting auth cookies...')
    response = requests.post(url=PROMETHEI_LOGIN_URL, data=BODY4LOGIN, 
                             headers=HEADERS4LOGIN)
    logger.info('auth cookies have been received')
    auth_cookie = response.cookies.get_dict()
    return auth_cookie


def get_events_list(cookies: dict) -> list[dict]:
    """
    sends a request to receive "Мои мероприятия", processes (encoding, formatting), returns data in the form of a dictionary list (json)

    Args:
        cookies (dict): auth cookies

    Returns:
        list[dict]: list of "my events"
    """
    logger.info('requesting list of events...')
    response = requests.get(url=EVENTS_GETTER_URL,
                            headers=HEADERS4EVENTS,
                            cookies=cookies)
    logger.info('"my events" list have been received')
    
    logger.info('processing...')
    encoding = get_response_encoding(response)                              # <?xml version="1.0" encoding="utf-8"?>
    soup = BeautifulSoup(response.content, "xml", from_encoding=encoding)   # xml -> python_obj
    data = extract_data(soup)                                               # clear: del extra fields and convert to dict
    logger.info(f'items processed: {len(data)}')
    return data
    

def save_event_to_json(data: list[dict]):
    new_file = pathlib.Path(__file__).parent / f"my_events_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(new_file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=4, ensure_ascii=False))
    logger.info(f'data have been stored to file: {new_file}')


if __name__ == '__main__':
    auth_cookie = get_auth_cookie()
    events = get_events_list(auth_cookie)
    save_event_to_json(events)
