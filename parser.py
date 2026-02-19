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


MAIN_INFO_URL = os.getenv('MAIN_INFO_URL')
HEADERS4MAIN_INFO = {
    "Sec-Ch-Ua": 'Not(A:Brand";v="8", "Chromium";v="144"',
    "Sec-Ch-Ua-Platform": "Windows",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "frame",
    "Referer": "https://dot.mpei.ac.ru/close/students/info.asp",
    "Priority": "u=0, i",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
}


def extract_dates(s: str) -> tuple[str, str]:
    if ':' in s:
        start = datetime.now().strftime('%Y-%m-%d')
        end = datetime.strptime(s.split('до')[-1].strip().split(' ')[0], '%d.%m.%Y').strftime('%Y-%m-%d')
        return (start, end)
    
    s = s.lstrip('с ')
    dates = tuple(map(lambda x: datetime.strptime(x.strip(), '%d.%m.%Y').strftime('%Y-%m-%d'), s.split('до')))
    return tuple(dates)


def extract_events(soup: BeautifulSoup) -> list[dict]:
    events_tables = soup.find('div', id='events').find_all('tbody')

    events = []
    for tbody in events_tables:
        rows = tbody.find_all('tr')
        for row in rows:
            fields = row.find_all('td')
            dates = extract_dates(fields[0].text)
            events.append({
                'date_start': dates[0],
                'date_end': dates[-1],
                'course_name': row.find('td', class_='course-name').text,
                'event_name': row.find('td', class_='element-name').text,
            })

    return events    


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
    sends a request to receive main page, processes (extract events, formatting), returns data in the form of a dictionary list (json)

    Args:
        cookies (dict): auth cookies

    Returns:
        list[dict]: list of "my events"
    """    
    logger.info('requesting list of events...')
    response = requests.get(url=MAIN_INFO_URL,
                            headers=HEADERS4MAIN_INFO, cookies=(cookies | {'etab': 'events'}))
    logger.info('main page have been received')
    soup = BeautifulSoup(response.content, "html.parser")
    
    logger.info('processing...')
    events = extract_events(soup)
    logger.info(f'items processed: {len(events)}')
    
    return events
    

def save_event_to_json(data: list[dict]):
    new_file = pathlib.Path(__file__).parent / f"my_events_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(new_file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=4, ensure_ascii=False))
    logger.info(f'data have been stored to file: {new_file}')


if __name__ == '__main__':
    auth_cookie = get_auth_cookie()
    events = get_events_list(auth_cookie)
    save_event_to_json(events)
