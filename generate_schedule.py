from io import BytesIO

import discord
from datetime import datetime, timedelta
from main_screenshot import DiscordClient

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
from PIL import Image, ImageDraw, ImageFont
import requests

class ImageGenerator():
    async def send_image(self, selected_date, ctx):
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')

        driver = webdriver.Chrome(options=options)
        driver.get(f'https://m.sports.naver.com/kbaseball/schedule/index?date=2024-{selected_date}')

        try:
            schedule_area = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="content"]/div/div[4]/div[1]'))
            )
            img = schedule_area.screenshot_as_png  # 스크린샷 캡처
            with open('standing/img.png', 'wb') as f:
                f.write(img)
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            img = None
        finally:
            driver.quit()

        with BytesIO() as image_binary:
            date_temp = datetime.strptime(str(datetime.today().year) + '-' + selected_date, '%Y-%m-%d').date()

            if date_temp.weekday() == 0:
                result = Image.new('RGB', (800, 70), color=(0, 0, 0))
                d = ImageDraw.Draw(result)
                title_font = ImageFont.truetype("malgunbd.ttf", 30)
                d.text((15, 15), f'{selected_date}은 경기가 없는 날입니다.', font=title_font, fill=(42, 242, 148))

            if img is None:
                result = Image.new('RGB', (800, 70), color=(0, 0, 0))
                d = ImageDraw.Draw(result)
                title_font = ImageFont.truetype("malgunbd.ttf", 30)
                d.text((15, 15), f'{selected_date}의 경기일정을 찾을 수 없습니다.', font=title_font, fill=(42, 242, 148))
                result.save(image_binary, format='PNG')
            else:
                image = Image.open('standing/img.png')
                image.save(image_binary, format='PNG')

            image_binary.seek(0)
            discord_file = discord.File(fp=image_binary, filename=f'{selected_date}.png')
            await ctx.send(file=discord_file)