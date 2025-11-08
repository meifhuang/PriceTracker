from selenium import webdriver
from selenium.webdriver.common.by import By
import time

url = 'https://www.amazon.com/Nulo-Turkey-Chicken-Canned-Ounce/dp/B06WV774HB/ref=sr_1_1?crid=38XFG58DIAZV8&dib=eyJ2IjoiMSJ9.vUsDglw4Xwvs_XMBEvbe4cbxsnLF6qTXqwDP9GqVl6FM90GEJodNzwFPPzBNVrCT7xlnuJbikrmZXzg0Yr988FK6qrNy8RRzSsfP7VA6OYuo-gpD55JpYqNZcfmEjUAHdoy8tuikKghym6DEHMfKDIPIVzcJksfV7jx4PO3sDx1KZZ-FaLSNqeT6Dt60zR_SoaewDxAX7vYg35hjkLsJcR-2TIojOOLGhLg2Z6jx8Txw984wdfuWpF_2PHyZrI_o4yBOE4BFwap_HWQzp4Oa9pS2H2_XeAtmHf7Q1DRh524.JFQ20IuUoxnK7OVuFLE68JSGBfiSIryFgXvZQN6rCIA&dib_tag=se&keywords=nulo%2Bcat%2Bfood%2Bwet%2Bcat%2Bchicken%2Band%2Bturkey%2B12.5%2Boz&qid=1762575756&sprefix=nulo%2Bcat%2Bfood%2Bwet%2Bcat%2Bchicken%2Band%2Bturkey%2B12.5%2Boz%2Caps%2C94&sr=8-1&th=1'

driver = webdriver.Chrome()

driver.get(url)
time.sleep(3)

whole_price = driver.find_element(by=By.CLASS_NAME, value="a-price-whole")
fraction_price = driver.find_element(by=By.CLASS_NAME, value="a-price-fraction")

price = int(whole_price.text) + (int(fraction_price.text) * .01)
print(price)
price_per_unit = driver.find_element(by=By.CLASS_NAME, value="a-text-price") 

print(price_per_unit.text)
driver.quit()

# print(price_per_unit)



