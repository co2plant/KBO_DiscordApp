from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import discord

class DiscordClient():
    def getSchedule(self, selected_date):
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')

        driver = webdriver.Chrome(options=options)
        driver.get(f'https://m.sports.naver.com/kbaseball/schedule/index?date=2024-{selected_date}')

        time.sleep(2)  # 페이지 로딩을 위한 대기 시간

        scheduleArea = driver.find_element(By.XPATH, '//*[@id="content"]/div/div[4]/div[1]')
        img = scheduleArea.screenshot_as_png()  # 스크린샷 캡처

        driver.quit()

        return img

    async def send_image(self, selected_date, ctx):
        img_bytes = self.getSchedule(selected_date)  # 스크린샷 캡처
        with BytesIO(img_bytes) as image_binary:
            image = Image.open(image_binary)
            image_binary.seek(0)
            discord_file = discord.File(fp=image_binary, filename=f'{selected_date}.png')
            await ctx.send(file=discord_file)  # Discord 채널에 이미지 전송