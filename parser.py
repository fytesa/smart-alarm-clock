import requests
from bs4 import BeautifulSoup
import re

def fetch_week_parity():
    url = "https://edu.sfu-kras.ru/timetable?group=КИ23-16%2F1б+%282+подгруппа%29"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        print("Ошибка при получении страницы:", e)
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    # Регулярное выражение ищет строки вида "Идёт чётная неделя" или "Идёт нечётная неделя"
    pattern = re.compile(r'Идёт\s+(ч[её]тная|неч[её]тная)\s+неделя', re.IGNORECASE)
    for text in soup.stripped_strings:
        match = pattern.search(text)
        if match:
            word = match.group(1).lower()
            if "неч" in word:
                return "odd"
            elif "чет" in word:
                return "even"
    return None

if __name__ == "__main__":
    parity = fetch_week_parity()
    if parity:
        print("Актуальная неделя:", parity)
    else:
        print("Информация о чётности недели не найдена.")
