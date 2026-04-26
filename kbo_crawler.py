import database
from selenium import webdriver
from selenium.webdriver.common.by import By
import re


STANDINGS_URL = 'https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx'
STANDINGS_ROWS_XPATH = '//*[@id="cphContents_cphContents_cphContents_udpRecord"]/table/tbody/tr'
SCHEDULE_URL = 'https://www.koreabaseball.com/Schedule/Schedule.aspx'
SCHEDULE_ROWS_XPATH = '//*[@id="tblScheduleList"]/tbody/tr'


def _create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')
    return webdriver.Chrome(options)


def _build_game_id(selected_date, game_index):
    return f'{selected_date}{game_index:02d}'


def _fetch_standings_rows(driver):
    driver.get(STANDINGS_URL)
    return driver.find_elements(By.XPATH, STANDINGS_ROWS_XPATH)


def _fetch_schedule_rows(driver):
    driver.get(SCHEDULE_URL)
    return driver.find_elements(By.XPATH, SCHEDULE_ROWS_XPATH)


def _split_matchup_text(matchup_text):
    separated_matchup = matchup_text.split('vs')
    team = ['', '']
    score = ['', '']

    for index in range(2):
        for word in list(separated_matchup[index]):
            if word.isdigit():
                score[index] += word
            else:
                team[index] += word

    return team, score


def insert_standings():
    driver = None
    try:
        driver = _create_driver()
        standingsArea = _fetch_standings_rows(driver)

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
        standingsArea = _fetch_standings_rows(driver)

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
    driver = None
    try:
        driver = _create_driver()
        scheduleArea = _fetch_schedule_rows(driver)

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

            if(i==count-rowspan_value):
                team, score = _split_matchup_text(tds[2].text)
                database.update_game_and_score([game_id, tds[1].text, team[0], score[0], score[1], team[1], tds[7].text, tds[8].text])
            else:
                team, score = _split_matchup_text(tds[1].text)
                database.update_game_and_score([game_id, tds[0].text, team[0], score[0], score[1], team[1], tds[6].text, tds[7].text])
    finally:
        if driver is not None:
            driver.quit()

def update_score(selected_date):
    driver = None
    try:
        driver = _create_driver()
        scheduleArea = _fetch_schedule_rows(driver)

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

            team, score = _split_matchup_text(separated_row[i+1])

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
        scheduleArea = _fetch_schedule_rows(driver)

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

            team, score = _split_matchup_text(separated_row[i+1])

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
