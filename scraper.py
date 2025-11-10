import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import time, random
from datetime import datetime
import psycopg2
import os
from dotenv import load_dotenv
from psycopg2 import OperationalError


load_dotenv()

# --- Setup logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("price_tracker.log", mode="a"),
        logging.StreamHandler()
    ]
)

def scrape_chewy(driver):
    url = 'https://www.chewy.com/nulo-freestyle-turkey-chicken-recipe/dp/168510'
    try:
        driver.get(url)
        time.sleep(random.uniform(3.0, 6.0))
        sale_price = driver.find_elements(by=By.CLASS_NAME, value="styles_priceNoDeal__JGk8L")
        if not sale_price:
            logging.warning(f"No price found on Chewy page:")
            return None
        price = sale_price[0].text.splitlines()[-1].replace('$', '').strip()
        pack_size = "12 cans"
        unit_oz = 12.5
        price_per_oz = (float(price) / 12.0) / unit_oz
    
        return {
            'company': 'Chewy',
            'price': price,
            'price_per_oz': round(price_per_oz, 2),  # Round to 2 decimals
            'pack_size': pack_size,
            'url': url
        }
    except Exception as e:
        logging.error(f"Failed to scrape from chewy: {e}")
        return None

def scrape_amazon(driver):
    url = 'https://www.amazon.com/Nulo-Turkey-Chicken-Canned-Ounce/dp/B06WV774HB'
    try:
        driver.get(url)
        time.sleep(random.uniform(3.0, 6.0))
        whole_price = driver.find_elements(by=By.CLASS_NAME, value="a-price-whole")
        fraction_price = driver.find_elements(by=By.CLASS_NAME, value="a-price-fraction")
        
        if not whole_price or not fraction_price:
            logging.error(f"Failed to scrape from Amazon:{e}")
        price = int(whole_price[0].text) + (int(fraction_price[0].text) * .01)
        pack_size = "12 cans"
        unit_oz = 12.5
        price_per_oz = (price / 12) / unit_oz

        return {
            'company': 'Amazon',
            'price': price,
            'price_per_oz': round(price_per_oz, 2),  # Round to 2 decimals
            'pack_size': pack_size,
            'url': url
        }

    except Exception as e:
        logging.error(f"Failed to scrape from amazon: {e}")
        return None

def scrape_petco(driver):
    url = 'https://www.petco.com/shop/en/petcostore/product/nulo-medalseries-grain-free-turkey-and-chicken-wet-cat-food'
    try:
        driver.get(url)
        time.sleep(random.uniform(3.0, 6.0))
        sale_price = driver.find_elements(by=By.CLASS_NAME, value="purchase-type-selector-styled__PurchaseTypePrice-sc-663c57fc-1")
        if not sale_price:
            logging.warning(f"No price found on Petco page:")
            return None
        price_clean = float(sale_price[0].text.replace('$','').strip())
        pack_size = "12 cans"
        unit_oz = 12.5
        price_per_oz = (price_clean / 12) / unit_oz
        return {
            'company': 'Petco',
            'price': price_clean,
            'price_per_oz': round(price_per_oz, 2), 
            'pack_size': pack_size,
            'url': url
        }
    
    except Exception as e:
        logging.error(f"Failed to scrape from Petco: {e}")
        return None

def scrape_petsmart(driver):
    url = 'https://www.petsmart.com/cat/food-and-treats/wet-food/nulo-medalseries--all-life-stages-wet-cat-food---grain-free-no-corn-wheat-and-soy-125-oz-36959.html'
    try:
        driver.get(url)
        time.sleep(random.uniform(3.0, 6.0))
        sale_price = driver.find_elements(by=By.CLASS_NAME, value="sparky-c-price--sale")
        og_price = driver.find_elements(by=By.CLASS_NAME, value="sparky-c-price")
        price_str = sale_price[0].text if sale_price else og_price[0].text if og_price else None
        
        if not price_str:
            logging.warning(f"No price found on Petsmart page")
            return None
        
        price_clean = float(price_str.replace('$', '').strip())
        
        pack_size = "1 can"
        unit_oz = 12.5
        price_per_oz = price_clean / unit_oz
        
        return {
            'company': 'PetSmart',
            'price': price_clean,
            'price_per_oz': round(price_per_oz, 2),  # Round to 2 decimals
            'pack_size': pack_size,
            'url': url
        }
    
    except Exception as e:
        logging.error(f"Failed to scrape from Petsmart: {e}")
        return None
    
def insert_price_record(cursor, product_data):
    """
    Insert a new price record into the database.
    product_data should be a dict or object with:
    product, company, url, price, price_per_oz, pack_size
    """
    product = "Nulo Turkey and Chicken Pate Canned Cat Food"
    try:
        cursor.execute(
            '''
            INSERT INTO "prices" (product, company, url, date, price, price_per_oz, pack_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''',
            (
                product,
                product_data['company'],
                product_data['url'],
                datetime.now(),
                product_data['price'],
                product_data['price_per_oz'],
                product_data['pack_size'],
            )
        )
        logging.info(f"Inserted {product_data['company']} at {product_data['price']}")
    except Exception as e:
        logging.error(f"Failed to insert record for {product_data.get('company')}: {e}")

def connect_with_retry(url, retries=5, delay=5):
    for i in range(retries):
        try:
            conn = psycopg2.connect(url, sslmode="require")
            return conn
        except OperationalError as e:
            print(f"Postgres connection failed ({i+1}/{retries}): {e}")
            time.sleep(delay)
    raise OperationalError(f"Could not connect after {retries} attempts")

def run_scraper():
    options = uc.ChromeOptions()
    options.add_argument("--incognito")
    options.add_argument(
    "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36")
    # options.add_argument("--headless=new")  # modern headless mode
    options.add_argument("--no-sandbox")  # required for CI environments
    options.add_argument("--disable-dev-shm-usage")  # shared memory issue in Docker/CI
    if os.getenv("CI") == "true":
        options.add_argument("--headless")
    
    
    driver = uc.Chrome(options=options)
    url = os.getenv("db_url")

    try:
        pg_conn = connect_with_retry(url)
        with pg_conn.cursor() as pg_cursor:
            for scrape in [scrape_petsmart, scrape_petco, scrape_chewy, scrape_amazon]:
                try:
                    record = scrape(driver)
                    if record:
                        insert_price_record(pg_cursor,record)
                        pg_conn.commit() 
                except Exception as e:
                    pg_conn.rollback()
                    logging.warning(f"{scrape} failed {e}")
            print("Scraped and inserted data")
    
    except psycopg2.OperationalError as e:
        print(f"Error connecting to PostgreSQL: {e}")
        raise

    except Exception as e:
        print(f"Error : {e}")
        
    finally: 
        driver.quit()
 

run_scraper()


