from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

class DiscordClients():
    scheduleArea = None

    def getEmblem(self, team):
        team_dict = {
            '두산': 'OB',
            '롯데': 'LT',
            '삼성': 'SS',
            'KIA': 'HT',
            '한화': 'HH',
            'NC': 'NC',
            'LG': 'LG',
            'SSG': 'SK',
            'KT': 'KT',
            '키움': 'WO'
        }
        url = 'https://sports-phinf.pstatic.net/team/kbo/default/{}'.format(team_dict[team]+'.png?type=f108_108')
        response = requests.get(url).content
        img = Image.open(BytesIO(response)).convert("RGBA")
        return img.resize((40,40))

    @staticmethod
    def getSchedule(self, selected_date):
        s = time.time()
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('no-sandbox')

        driver = webdriver.Chrome(options)
        driver.get('https://www.koreabaseball.com/Schedule/Schedule.aspx')

        scheduleArea = driver.find_elements(By.XPATH, '//*[@id="tblScheduleList"]/tbody/tr')



        #result = '날짜|시간||경기||구장|비고\n---|---|---|---|---|---|---\n'
        result =''

        count = 0
        rowspan_value = 0
        isloop = False
        #scheduleArea는 tr태그들을 담고 있는 리스트
        #tr태그들은 각각의 경기를 나타냄
        #row로 끄집어내서 해당 일자에 맞는 경기를 찾아내는 로직
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


        ###########################################################################################################
        #이미지 생성 기능

        im = Image.new("RGB", (800, (rowspan_value+1)*70), (0, 0, 0))
        title_image = Image.new("RGB", (800, 70), (39, 39, 39))
        line = Image.new("RGB", (800, 2), (39, 39, 39))

        im.paste(title_image, (0, 0))

        for i in range(1, rowspan_value+1):
            im.paste(line, (0, i * 70))

        title_font = ImageFont.truetype("malgunbd.ttf", 30)
        content_font = ImageFont.truetype("malgunbd.ttf", 26)
        d = ImageDraw.Draw(im)
        d.text((15, 15), '{0} KBO 정규리그 경기일정'.format(selected_date), font=title_font, fill=(42,242,148))
        ###########################################################################################################

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
                result += f"{selected_date}|{tds[1].text}|{team[0]}|{score[0]} vs {score[1]}|{team[1]}|{tds[7].text}|{tds[8].text}\n"
                d.text((15, 18 + (i-count+rowspan_value+1) * 70), tds[1].text, font=content_font, fill=(242,242,242))
                d.text((100, 18 + (i-count+rowspan_value+1) * 70), f"{tds[7].text}", font=content_font, fill=(242,242,242))
                d.text((250, 18 + (i-count+rowspan_value+1) * 70), f"{team[0]}", font=content_font, fill=(242,242,242)) #어웨이팀
                im.paste(self.getEmblem(team[0]), (300, 15+(i-count+rowspan_value+1) * 70))
                d.text((400, 18 + (i-count+rowspan_value+1) * 70), f"{score[0]}  vs  {score[1]}", font=content_font, fill=(217,43,4)) #점수
                im.paste(self.getEmblem(team[1]), (550, 15+(i-count+rowspan_value+1) * 70))
                d.text((600, 18 + (i-count+rowspan_value+1) * 70), f"{team[1]}", font=content_font, fill=(242,242,242)) #홈팀
                d.text((700, 18 + (i-count+rowspan_value+1) * 70), f"{tds[8].text}", font=content_font, fill=(242,242,242))
            else:
                temp = tds[1].text.split('vs')
                for j in range(2):
                    for word in list(temp[j]):
                        if word.isdigit():
                            score[j]+=word
                        else:
                            team[j]+=word
                result += f"{selected_date}|{tds[0].text}|{team[0]}|{score[0]} vs {score[1]}|{team[1]}|{tds[6].text}|{tds[7].text}\n"
                d.text((15, 18 + (i-count+rowspan_value+1) * 70), tds[0].text, font=content_font, fill=(242,242,242)) #시간
                d.text((100, 18 + (i-count+rowspan_value+1) * 70), f"{tds[6].text}", font=content_font, fill=(242,242,242)) #구장
                d.text((250, 18 + (i-count+rowspan_value+1) * 70), f"{team[0]}", font=content_font, fill=(242,242,242)) #어웨이팀
                im.paste(self.getEmblem(team[0]), (300, 15+(i-count+rowspan_value+1) * 70))
                d.text((400, 18 + (i-count+rowspan_value+1) * 70), f"{score[0]}  vs  {score[1]}", font=content_font, fill=(217,43,4)) #점수
                im.paste(self.getEmblem(team[1]), (550, 15+(i-count+rowspan_value+1) * 70))
                d.text((600, 18 + (i-count+rowspan_value+1) * 70), f"{team[1]}", font=content_font, fill=(242,242,242)) #홈팀
                d.text((700, 18 + (i-count+rowspan_value+1) * 70), f"{tds[7].text}", font=content_font, fill=(242,242,242)) #비고(우천 취소 등)

        return im