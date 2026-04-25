import database
from selenium import webdriver
from selenium.webdriver.common.by import By
from html.parser import HTMLParser
import re
from datetime import datetime


def _create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')
    return webdriver.Chrome(options)


def _export_sql_snapshot_safely():
    try:
        dump_path = database.export_sql_snapshot()
        print(f'Exported SQL snapshot: {dump_path}')
        return dump_path
    except Exception as exc:
        print(f'Error exporting SQL snapshot: {exc}')
        return None


def _build_game_id(selected_date, game_index):
    return f'{selected_date}{game_index:02d}'


RUNNER_STATE_LABEL_TO_KEY = {
    'BASES EMPTY': 'bases_empty',
    'RUNNERS ON': 'runners_on',
    'ONLY 1ST BASE': 'runner_on_1',
    'ONLY 2ND BASE': 'runner_on_2',
    'ONLY 3RD BASE': 'runner_on_3',
    '1ST + 2ND BASE': 'runner_on_1_2',
    '1ST + 3RD BASE': 'runner_on_1_3',
    '2ND + 3RD BASE': 'runner_on_2_3',
    'BASED ON LOADED': 'bases_loaded',
    'BASES LOADED': 'bases_loaded',
    'SCORING POSITION': 'scoring_position',
}


def normalize_runner_state_label(label):
    normalized = re.sub(r'\s+', ' ', label.strip().upper())
    return RUNNER_STATE_LABEL_TO_KEY.get(normalized)


def _clean_text(value):
    return re.sub(r'\s+', ' ', value).strip()


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self._table_stack = []
        self._current_row = None
        self._current_cell = None
        self._capture_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self._table_stack.append([])
        elif tag == 'tr' and self._table_stack:
            self._current_row = []
        elif tag in ('td', 'th') and self._current_row is not None:
            self._current_cell = []
            self._capture_cell = True

    def handle_data(self, data):
        if self._capture_cell and self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self._current_row is not None and self._current_cell is not None:
            self._current_row.append(_clean_text(''.join(self._current_cell)))
            self._current_cell = None
            self._capture_cell = False
        elif tag == 'tr' and self._table_stack and self._current_row is not None:
            if any(self._current_row):
                self._table_stack[-1].append(self._current_row)
            self._current_row = None
        elif tag == 'table' and self._table_stack:
            self.tables.append(self._table_stack.pop())


def _parse_tables(html):
    parser = _TableParser()
    parser.feed(html)
    return parser.tables


def _parse_int(value):
    cleaned = value.replace(',', '').strip()
    if cleaned in ('', '-', 'No Data Available'):
        return None
    return int(cleaned)


def _parse_decimal(value):
    cleaned = value.strip()
    if cleaned in ('', '-', 'No Data Available'):
        return None
    if cleaned.startswith('.'):
        cleaned = f'0{cleaned}'
    return float(cleaned)


def _rate(numerator, denominator):
    if denominator in (None, 0):
        return None
    return round(numerator / denominator, 3)


def _slash_line(ab, hits, doubles, triples, homers, walks, hit_by_pitch):
    if None in (ab, hits, doubles, triples, homers):
        return None, None, None
    walks = walks or 0
    hit_by_pitch = hit_by_pitch or 0
    singles = hits - doubles - triples - homers
    total_bases = singles + (2 * doubles) + (3 * triples) + (4 * homers)
    avg = _rate(hits, ab)
    obp = _rate(hits + walks + hit_by_pitch, ab + walks + hit_by_pitch)
    slg = _rate(total_bases, ab)
    ops = None if obp is None or slg is None else round(obp + slg, 3)
    return obp, slg, ops


def discover_hitter_player_ids(html):
    seen = set()
    player_ids = []
    for player_id in re.findall(r'playerinfohitter/summary\.aspx\?pcode=(\d+)', html, re.IGNORECASE):
        if player_id not in seen:
            seen.add(player_id)
            player_ids.append(player_id)
    return player_ids


def discover_pitcher_player_ids(html):
    seen = set()
    player_ids = []
    for player_id in re.findall(r'playerinfopitcher/summary\.aspx\?pcode=(\d+)', html, re.IGNORECASE):
        if player_id not in seen:
            seen.add(player_id)
            player_ids.append(player_id)
    return player_ids


def normalize_count_state_label(label):
    normalized = label.strip()
    if re.fullmatch(r'[0-3]-[0-2]', normalized) is None:
        return None
    balls, strikes = normalized.split('-')
    return f'count_{balls}_{strikes}'


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texts = []
        self._ignored_tag_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._ignored_tag_depth += 1

    def handle_data(self, data):
        if self._ignored_tag_depth:
            return
        text = _clean_text(data)
        if text:
            self.texts.append(text)

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self._ignored_tag_depth:
            self._ignored_tag_depth -= 1


def _parse_texts(html):
    parser = _TextParser()
    parser.feed(html)
    return parser.texts


def parse_player_profile(html, player_id):
    texts = _parse_texts(html)
    compact_text = _clean_text(' '.join(texts))
    profile_text = compact_text
    profile_start = re.search(r'player info\s+', compact_text, re.IGNORECASE)
    if profile_start:
        profile_text = compact_text[profile_start.start():]

    def extract(label):
        prefix = f'{label} :'
        for text in texts:
            if text.startswith(prefix):
                return _clean_text(text.removeprefix(prefix))
        labels = 'Name|Position|No|Salary|Born|Debut|HT/WT|Transaction'
        pattern = rf'{label}\s*:\s*(.*?)(?=\s+(?:{labels})\s*:|\s+Summary\b|$)'
        match = re.search(pattern, profile_text, re.IGNORECASE)
        return _clean_text(match.group(1)) if match else None

    team_name = ''
    team_match = re.search(r'player info\s+([A-Z0-9 &.\-]+?)\s+Name\s*:', profile_text, re.IGNORECASE)
    if not team_match:
        team_match = re.search(r'([A-Z0-9 &.\-]+?)\s+Name\s*:', profile_text)
    if team_match:
        team_name = _clean_text(team_match.group(1))
        team_name = _clean_text(re.sub(r'^(?:player info\s+)+', '', team_name, flags=re.IGNORECASE))

    profile = {'player_id': player_id, 'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    profile['name'] = extract('Name')
    profile['position'] = extract('Position')
    profile['salary'] = extract('Salary')
    profile['born'] = extract('Born')
    profile['debut'] = extract('Debut')
    profile['height_weight'] = extract('HT/WT')
    profile['team_name'] = team_name
    return profile


def parse_runner_state_stats(html, player_id, team_name, season, source_updated_at=None):
    for table in _parse_tables(html):
        if not table:
            continue
        header = [cell.upper() for cell in table[0]]
        if 'RUNNER' not in header:
            continue
        column_index = {name: index for index, name in enumerate(header)}
        rows = []
        for cells in table[1:]:
            runner_label = cells[column_index['RUNNER']] if column_index['RUNNER'] < len(cells) else ''
            split_key = normalize_runner_state_label(runner_label)
            if split_key is None:
                continue
            ab = _parse_int(cells[column_index['AB']]) if 'AB' in column_index and column_index['AB'] < len(cells) else None
            bb = _parse_int(cells[column_index['BB']]) if 'BB' in column_index and column_index['BB'] < len(cells) else 0
            hbp = _parse_int(cells[column_index['HBP']]) if 'HBP' in column_index and column_index['HBP'] < len(cells) else 0
            hits = _parse_int(cells[column_index['H']])
            doubles = _parse_int(cells[column_index['2B']])
            triples = _parse_int(cells[column_index['3B']])
            homers = _parse_int(cells[column_index['HR']])
            obp, slg, ops = _slash_line(ab, hits, doubles, triples, homers, bb, hbp)
            rows.append({
                'season': season,
                'entity_type': 'player',
                'entity_id': player_id,
                'team_name': team_name,
                'split_type': 'runner_state',
                'split_key': split_key,
                'pa': (ab or 0) + (bb or 0) + (hbp or 0),
                'ab': ab,
                'h': hits,
                'double_hits': doubles,
                'triple_hits': triples,
                'hr': homers,
                'rbi': _parse_int(cells[column_index['RBI']]),
                'bb': bb,
                'hbp': hbp,
                'so': _parse_int(cells[column_index['SO']]),
                'gidp': _parse_int(cells[column_index['GIDP']]),
                'avg': _parse_decimal(cells[column_index['AVG']]),
                'obp': obp,
                'slg': slg,
                'ops': ops,
                'source_updated_at': source_updated_at,
            })
        return rows
    return []


def parse_pitcher_count_stats(html, player_id, team_name, season, source_updated_at=None):
    for table in _parse_tables(html):
        if not table:
            continue
        header = [cell.upper() for cell in table[0]]
        if 'COUNT(B-S)' not in header:
            continue
        column_index = {name: index for index, name in enumerate(header)}
        rows = []
        for cells in table[1:]:
            count_label = cells[column_index['COUNT(B-S)']] if column_index['COUNT(B-S)'] < len(cells) else ''
            split_key = normalize_count_state_label(count_label)
            if split_key is None:
                continue
            rows.append({
                'season': season,
                'entity_type': 'player',
                'entity_id': player_id,
                'team_name': team_name,
                'split_type': 'count_state',
                'split_key': split_key,
                'h': _parse_int(cells[column_index['H']]),
                'double_hits': _parse_int(cells[column_index['2B']]),
                'triple_hits': _parse_int(cells[column_index['3B']]),
                'hr': _parse_int(cells[column_index['HR']]),
                'bb': _parse_int(cells[column_index['BB']]),
                'hbp': _parse_int(cells[column_index['HBP']]),
                'so': _parse_int(cells[column_index['K']]),
                'wp': _parse_int(cells[column_index['WP']]),
                'bk': _parse_int(cells[column_index['BK']]),
                'avg': _parse_decimal(cells[column_index['OAVG']]),
                'source_updated_at': source_updated_at,
            })
        return rows
    return []


def refresh_situational_stats_if_stale(season=None):
    if season is None:
        season = datetime.now().year
    now = datetime.now()
    if not database.should_refresh_situational_stats(now):
        has_count_state_rows = getattr(database, 'has_situational_stats', lambda _split_type: True)('count_state')
        if has_count_state_rows:
            return False

    driver = None
    try:
        driver = _create_driver()
        driver.get('https://eng.koreabaseball.com/Stats/BattingByTeams.aspx')
        player_ids = discover_hitter_player_ids(driver.page_source)
        source_updated_at = now.strftime('%Y-%m-%d %H:%M:%S')

        for player_id in player_ids:
            driver.get(f'https://eng.koreabaseball.com/Teams/PlayerInfoHitter/Summary.aspx?pcode={player_id}')
            profile = parse_player_profile(driver.page_source, player_id)
            profile['updated_at'] = source_updated_at
            database.upsert_player(profile)

            driver.get(f'https://eng.koreabaseball.com/Teams/PlayerInfoHitter/SituationsRunner.aspx?pcode={player_id}')
            rows = parse_runner_state_stats(driver.page_source, player_id, profile['team_name'], season, source_updated_at)
            for row in rows:
                database.upsert_situational_stat(row)

        driver.get('https://eng.koreabaseball.com/Stats/PitchingLeaders.aspx')
        pitcher_ids = discover_pitcher_player_ids(driver.page_source)
        for player_id in pitcher_ids:
            driver.get(f'https://eng.koreabaseball.com/Teams/PlayerInfoPitcher/Summary.aspx?pcode={player_id}')
            profile = parse_player_profile(driver.page_source, player_id)
            profile['updated_at'] = source_updated_at
            database.upsert_player(profile)

            driver.get(f'https://eng.koreabaseball.com/Teams/PlayerInfoPitcher/SituationsCount.aspx?pcode={player_id}')
            rows = parse_pitcher_count_stats(driver.page_source, player_id, profile['team_name'], season, source_updated_at)
            for row in rows:
                database.upsert_situational_stat(row)
        _export_sql_snapshot_safely()
        return True
    finally:
        if driver is not None:
            driver.quit()

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
            win = tds[3].text
            lose = tds[4].text
            draw = tds[5].text
            rate = tds[6].text
            last_10 = tds[8].text
            streak = tds[9].text
            home = tds[10].text
            away = tds[11].text
            database.insert_standings([id, team, win, lose, draw, rate, last_10, streak, home, away])
        _export_sql_snapshot_safely()
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
            win = tds[3].text
            lose = tds[4].text
            draw = tds[5].text
            rate = tds[6].text
            last_10 = tds[8].text
            streak = tds[9].text
            home = tds[10].text
            away = tds[11].text
            database.update_standings([id, team, win, lose, draw, rate, last_10, streak, home, away])
        _export_sql_snapshot_safely()
    finally:
        if driver is not None:
            driver.quit()

def update_schedule_once(selected_date):
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
                if dates[0] == selected_date:
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
        _export_sql_snapshot_safely()
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
        temp = ['', '']

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
        temp = ['', '']

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
        _export_sql_snapshot_safely()
    finally:
        if driver is not None:
            driver.quit()

if __name__ == '__main__':
    insert_schedule_month()
