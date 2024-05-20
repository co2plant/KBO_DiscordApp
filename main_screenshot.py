from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

class DiscordClient():
    scheduleArea = None
    def getSchedule(self, selected_date):
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')

        driver = webdriver.Chrome(options)
        driver.get('https://m.sports.naver.com/kbaseball/schedule/index?date=2024-05-21')

        time.sleep(2)

        scheduleArea = driver.find_element(By.XPATH, '//*[@id="content"]/div/div[4]/div[1]')

        path = 'C:/TEST/{0}.png'.format(selected_date)

        scheduleArea.screenshot(path)

        driver.quit()




DiscordClient.getSchedule(DiscordClient(), '05.12')