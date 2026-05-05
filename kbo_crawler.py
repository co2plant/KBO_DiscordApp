import database
from html.parser import HTMLParser
import json
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from selenium import webdriver
from selenium.webdriver.common.by import By
import re

_SCOREBOARD_URL = 'https://www.koreabaseball.com/Schedule/ScoreBoard.aspx'
_MOBILE_LIVE_BASE_URL = 'https://m.koreabaseball.com'
_DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; KBO-DiscordBot/1.0)',
}


def _create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')
    return webdriver.Chrome(options)


def _build_game_id(selected_date, game_index):
    return f'{selected_date}{game_index:02d}'


def _normalize_schedule_date(value):
    value = str(value).strip()
    match = re.search(r'(\d{1,2})\D+(\d{1,2})', value)
    if match:
        return f'{int(match.group(1)):02d}{int(match.group(2)):02d}'

    digits = ''.join(char for char in value if char.isdigit())
    return digits


def _attr_dict(attrs):
    return {name: value or '' for name, value in attrs}


def _has_class(attrs, class_name):
    classes = _attr_dict(attrs).get('class', '').split()
    return class_name in classes


def _parse_score(value):
    value = str(value).strip()
    return int(value) if value.isdigit() else -1


class _ScoreboardParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.games = []
        self._current = None
        self._div_depth = 0
        self._side = None
        self._team_capture = None
        self._score_capture = None
        self._state_capture = False
        self._place_capture = False
        self._place_parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'div' and _has_class(attrs, 'smsScore') and self._current is None:
            self._current = {
                'game_date': '',
                'game_id': '',
                'away_team': '',
                'home_team': '',
                'away_score': -1,
                'home_score': -1,
                'state': '-',
                'stadium': '',
                'time': '',
            }
            self._div_depth = 1
            return

        if self._current is None:
            return

        if tag == 'div':
            self._div_depth += 1

        if tag == 'p':
            if _has_class(attrs, 'leftTeam'):
                self._side = 'away'
            elif _has_class(attrs, 'rightTeam'):
                self._side = 'home'
            elif _has_class(attrs, 'place'):
                self._place_capture = True
                self._place_parts = []

        if tag == 'strong':
            if _has_class(attrs, 'teamT'):
                self._team_capture = self._side
            elif _has_class(attrs, 'flag'):
                self._state_capture = True

        if tag == 'em' and _has_class(attrs, 'score'):
            self._score_capture = self._side

        if tag == 'a':
            href = _attr_dict(attrs).get('href', '')
            if 'GameCenter/Main.aspx' in href:
                query = parse_qs(urlparse(href).query)
                self._current['game_date'] = query.get('gameDate', [''])[0]
                self._current['game_id'] = query.get('gameId', [''])[0]

    def handle_endtag(self, tag):
        if self._current is None:
            return

        if tag == 'strong':
            self._team_capture = None
            self._state_capture = False
        elif tag == 'em':
            self._score_capture = None
        elif tag == 'p':
            if self._place_capture:
                self._finish_place()
                self._place_capture = False
            self._side = None

        if tag == 'div':
            self._div_depth -= 1
            if self._div_depth == 0:
                self._finish_game()

    def handle_data(self, data):
        if self._current is None:
            return

        text = data.strip()
        if text == '':
            return

        if self._team_capture == 'away':
            self._current['away_team'] += text
        elif self._team_capture == 'home':
            self._current['home_team'] += text
        elif self._score_capture == 'away':
            self._current['away_score'] = _parse_score(text)
        elif self._score_capture == 'home':
            self._current['home_score'] = _parse_score(text)
        elif self._state_capture:
            self._current['state'] = text
        elif self._place_capture:
            self._place_parts.append(text)

    def _finish_place(self):
        place = ' '.join(self._place_parts).strip()
        match = re.match(r'(.+?)\s+(\d{1,2}:\d{2})$', place)
        if match:
            self._current['stadium'] = match.group(1).strip()
            self._current['time'] = match.group(2)
        else:
            self._current['stadium'] = place

    def _finish_game(self):
        if self._current['away_team'] and self._current['home_team']:
            self.games.append(self._current)
        self._current = None
        self._div_depth = 0
        self._side = None
        self._team_capture = None
        self._score_capture = None
        self._state_capture = False
        self._place_capture = False
        self._place_parts = []


def _parse_scoreboard_games(scoreboard_html):
    parser = _ScoreboardParser()
    parser.feed(scoreboard_html)
    return parser.games


def _request_text(url, data=None, headers=None):
    request_headers = dict(_DEFAULT_HEADERS)
    if headers is not None:
        request_headers.update(headers)

    body = None
    if data is not None:
        body = urlencode(data).encode('utf-8')
        request_headers.setdefault('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8')

    request = Request(url, data=body, headers=request_headers)
    with urlopen(request, timeout=10) as response:
        return response.read().decode('utf-8')


def _fetch_live_game_state(game_id):
    text = _request_text(
        f'{_MOBILE_LIVE_BASE_URL}/ws/Kbo.asmx/GetGameState',
        data={'le_id': '1', 'sr_id': '0', 'g_id': game_id},
        headers={
            'Referer': f'{_MOBILE_LIVE_BASE_URL}/Kbo/Live/Live.aspx?p_le_id=1&p_sr_id=0&p_g_id={game_id}&p_sc_id=0',
            'X-Requested-With': 'XMLHttpRequest',
        },
    )
    payload = json.loads(text)
    games = payload.get('game') or []
    return games[0] if games else None


def _live_game_status(live_game, fallback_status):
    if live_game is None:
        return fallback_status or '-'

    section_id = str(live_game.get('SECTION_ID', ''))
    if section_id == '1':
        return '경기전'
    if section_id == '3':
        return '경기종료'

    inning = live_game.get('INN_NO')
    tb_name = live_game.get('TB_NM')
    if inning and tb_name:
        return f'{inning}회{tb_name}'

    return fallback_status or '-'


def update_live_scores(selected_date):
    selected_date = _normalize_schedule_date(selected_date)
    scoreboard_html = _request_text(_SCOREBOARD_URL)
    scoreboard_games = [
        game for game in _parse_scoreboard_games(scoreboard_html)
        if game['game_date'] == '' or game['game_date'].endswith(selected_date)
    ]

    print(f'[crawl:live-score] date={selected_date} scoreboard_games={len(scoreboard_games)}')

    updated_count = 0
    for game in scoreboard_games:
        live_game = None
        if game['game_id']:
            try:
                live_game = _fetch_live_game_state(game['game_id'])
            except Exception as exc:
                print(f"[crawl:live-score] failed live state for {game['game_id']}: {exc}")

        away_score = game['away_score']
        home_score = game['home_score']
        if live_game is not None:
            away_score = _parse_score(live_game.get('A_SCORE_CN', away_score))
            home_score = _parse_score(live_game.get('H_SCORE_CN', home_score))

        status = _live_game_status(live_game, game['state'])
        database.update_live_game_score(
            selected_date,
            game['time'],
            game['away_team'],
            game['home_team'],
            away_score,
            home_score,
            status,
        )
        updated_count += 1
        print(
            f"[crawl:live-score] {game['time']} {game['away_team']} "
            f"{away_score}-{home_score} {game['home_team']} {status}"
        )

    return updated_count


def insert_standings():
    driver = None
    try:
        driver = _create_driver()
        driver.get('https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx')

        standingsArea = driver.find_elements(By.XPATH, '//*[@id="cphContents_cphContents_cphContents_udpRecord"]/table/tbody/tr')

        for row in standingsArea:
            tds = row.find_elements(By.TAG_NAME, 'td')
            id = tds[0].text
            team = tds[1].text
            win = tds[2].text
            lose = tds[3].text
            draw = tds[4].text
            rate = tds[6].text
            last_10 = tds[8].text
            streak = tds[9].text
            home = tds[10].text
            away = tds[11].text
            database.insert_standings([id, team, win, lose, draw, rate, last_10, streak, home, away])
    finally:
        if driver is not None:
            driver.quit()

def update_standings():
    driver = None
    try:
        driver = _create_driver()
        driver.get('https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx')

        standingsArea = driver.find_elements(By.XPATH, '//*[@id="cphContents_cphContents_cphContents_udpRecord"]/table/tbody/tr')

        for row in standingsArea:
            tds = row.find_elements(By.TAG_NAME, 'td')
            id = tds[0].text
            team = tds[1].text
            win = tds[2].text
            lose = tds[3].text
            draw = tds[4].text
            rate = tds[6].text
            last_10 = tds[8].text
            streak = tds[9].text
            home = tds[10].text
            away = tds[11].text
            database.update_standings([id, team, win, lose, draw, rate, last_10, streak, home, away])
    finally:
        if driver is not None:
            driver.quit()

def update_schedule_once(selected_date):
    selected_date = _normalize_schedule_date(selected_date)
    driver = None
    try:
        driver = _create_driver()
        driver.get('https://www.koreabaseball.com/Schedule/Schedule.aspx')

        scheduleArea = driver.find_elements(By.XPATH, '//*[@id="tblScheduleList"]/tbody/tr')

        count = 0
        rowspan_value = 0
        isloop = False

        for row in scheduleArea:
            if(isloop):
                break
            tds = row.find_elements(By.CLASS_NAME, 'day')
            for td in tds:
                dates = td.text.split('(')
                count+=int(td.get_attribute('rowspan'))
                if _normalize_schedule_date(dates[0]) == selected_date:
                    rowspan_value = int(td.get_attribute('rowspan'))
                    isloop = True
                    break

        for i in range(count-rowspan_value, count):
            tds = scheduleArea[i].find_elements(By.TAG_NAME, 'td')
            game_id = _build_game_id(selected_date, i - (count - rowspan_value))

            team = ['', '']
            score = ['', '']

            if(i==count-rowspan_value):
                temp = tds[2].text.split('vs')
                for j in range(2):
                    for word in list(temp[j]):
                        if word.isdigit():
                            score[j]+=word
                        else:
                            team[j]+=word
                database.update_game_and_score([game_id, tds[1].text, team[0], score[0], score[1], team[1], tds[7].text, tds[8].text])
            else:
                temp = tds[1].text.split('vs')
                for j in range(2):
                    for word in list(temp[j]):
                        if word.isdigit():
                            score[j]+=word
                        else:
                            team[j]+=word
                database.update_game_and_score([game_id, tds[0].text, team[0], score[0], score[1], team[1], tds[6].text, tds[7].text])
    finally:
        if driver is not None:
            driver.quit()

def update_score(selected_date):
    driver = None
    try:
        driver = _create_driver()
        driver.get('https://www.koreabaseball.com/Schedule/Schedule.aspx')

        scheduleArea = driver.find_elements(By.XPATH, '//*[@id="tblScheduleList"]/tbody/tr')

        id_format = None
        incount = 0
        temp = None

        for row in scheduleArea:
            i=1
            try:
                temp = row.find_element(By.CLASS_NAME, 'day').text
                temp = re.split(r'[.|(]', temp)
                incount = 0
            except:
                i=0
            id_format = temp[0]+temp[1]+str(incount).zfill(2) #무의미한 계산을 줄이기 위해 사용

            separated_row = row.text.split(' ')

            st = separated_row[i+1].split('vs')
            team = ['', '']
            score = ['', '']

            for j in range(2):
                for word in list(st[j]):
                    if word.isdigit():
                        score[j]+=word
                    else:
                        team[j]+=word

            if score[0] == '':
                score[0] = '-1'
            if score[1] == '':
                score[1] = '-1'
    finally:
        if driver is not None:
            driver.quit()


def insert_schedule_month():
    driver = None
    try:
        driver = _create_driver()
        driver.get('https://www.koreabaseball.com/Schedule/Schedule.aspx')

        scheduleArea = driver.find_elements(By.XPATH, '//*[@id="tblScheduleList"]/tbody/tr')

        id_format = None
        incount = 0
        temp = None

        for row in scheduleArea:
            i=1
            try:
                temp = row.find_element(By.CLASS_NAME, 'day').text
                temp = re.split(r'[.|(]', temp)
                incount = 0
            except:
                i=0
            id_format = temp[0]+temp[1]+str(incount).zfill(2) #무의미한 계산을 줄이기 위해 사용

            separated_row = row.text.split(' ')

            st = separated_row[i+1].split('vs')
            team = ['', '']
            score = ['', '']

            for j in range(2):
                for word in list(st[j]):
                    if word.isdigit():
                        score[j]+=word
                    else:
                        team[j]+=word

            if score[0] == '':
                score[0] = '-1'
            if score[1] == '':
                score[1] = '-1'

            print(f'{id_format, team[0], score[0], score[1], team[1], separated_row[-2], separated_row[-1]}')

            incount+=1

            database.insert_game_and_score([id_format, separated_row[i], team[0], score[0], score[1], team[1], separated_row[-2], separated_row[-1]])
    finally:
        if driver is not None:
            driver.quit()

if __name__ == '__main__':
    insert_schedule_month()
