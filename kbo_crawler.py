import database
from selenium import webdriver
from selenium.webdriver.common.by import By
import re

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
            database.insert_game_and_score([selected_date, tds[1].text, team[0], score[0], score[1], team[1], tds[7].text, tds[8].text])
        else:
            temp = tds[1].text.split('vs')
            for j in range(2):
                for word in list(temp[j]):
                    if word.isdigit():
                        score[j]+=word
                    else:
                        team[j]+=word
            database.insert_game_and_score([selected_date, tds[0].text, team[0], score[0], score[1], team[1], tds[6].text, tds[7].text])

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
        except:
            i=0
        id_format = temp[0]+temp[1]+str(incount) #무의미한 계산을 줄이기 위해 사용

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

        print(f'{id_format, team[0], score[0], score[1], team[1], separated_row[-2], separated_row[-1]}')

        incount+=1

        database.insert_game_and_score([id_format, temp[0], separated_row[i], team[0], score[0], score[1], team[1], separated_row[-2], separated_row[-1]])
    driver.quit()

while(True):
    if input() == '1':
        insert_schedule_month()
    else:
        update_schedule_once(input())
    if input() == 'n':
        break
    else:
        continue