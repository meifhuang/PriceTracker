from selenium import webdriver
from selenium.webdriver.common.by import By
import time

url = 'https://www.petsmart.com/cat/food-and-treats/wet-food/nulo-medalseries--all-life-stages-wet-cat-food---grain-free-no-corn-wheat-and-soy-125-oz-36959.html'

driver = webdriver.Chrome()

driver.get(url)
time.sleep(3)

sale_price = driver.find_element(by=By.CLASS_NAME, value="sparky-c-price--sale")
og_price = driver.find_element(by=By.CLASS_NAME, value="sparky-c-price")

print(sale_price.text)
print(og_price.text)
price_per_unit = float(sale_price.text[1:]) / 12.5
print(price_per_unit)
driver.quit()

# print(price_per_unit)



