import database
from selenium import webdriver
from selenium.webdriver.common.by import By
import re

def insert_standings():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')

    driver = webdriver.Chrome(options)
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

def update_standings():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')

    driver = webdriver.Chrome(options)
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
        database.update_standings([team, win, lose, draw, rate, last_10, streak, home, away, id])

def update_schedule_once(selected_date):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')

    driver = webdriver.Chrome(options)
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
            database.update_game_and_score([selected_date, tds[1].text, team[0], score[0], score[1], team[1], tds[7].text, tds[8].text])
        else:
            temp = tds[1].text.split('vs')
            for j in range(2):
                for word in list(temp[j]):
                    if word.isdigit():
                        score[j]+=word
                    else:
                        team[j]+=word
            database.update_game_and_score([selected_date, tds[0].text, team[0], score[0], score[1], team[1], tds[6].text, tds[7].text])

def update_score(selected_date):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')

    driver = webdriver.Chrome(options)
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


def insert_schedule_month():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('no-sandbox')

    driver = webdriver.Chrome(options)
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
    driver.quit()

insert_schedule_month()