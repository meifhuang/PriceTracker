from selenium import webdriver
from selenium.webdriver.common.by import By
import time

url = 'https://www.petco.com/shop/en/petcostore/product/nulo-medalseries-grain-free-turkey-and-chicken-wet-cat-food?srsltid=AfmBOoqWXFUtYNV3BBGJ6qCbpZdbG4vwhImhAdJzvub2KB5N3k2AIw6g'

driver = webdriver.Chrome()

driver.get(url)
time.sleep(5)

sale_price = driver.find_element(by=By.CLASS_NAME, value="purchase-type-selector-styled__PurchaseTypePrice-sc-663c57fc-1")
print(sale_price.text)

price_per_unit = int(sale_price.text) / 12.5

driver.quit()

# print(price_per_unit)



