import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import time, random, subprocess, os, re
from datetime import datetime
import psycopg2
from dotenv import load_dotenv
from psycopg2 import OperationalError
from database.connect_db import connect_with_retry

load_dotenv()

# --- Setup logging ---
logging.basicConfig(
    filename="price_tracker.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode='a'
)

def get_chrome_major_version():
    """Return installed Chrome major version (int) or None if not found."""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    ]
    for exe in candidates:
        if os.path.exists(exe):
            try:
                out = subprocess.check_output([exe, "--version"], stderr=subprocess.STDOUT).decode()
                m = re.search(r'(\d+)\.', out)
                if m:
                    return int(m.group(1))
            except Exception:
                continue

    # fallback to commands on PATH
    for cmd in (["google-chrome", "--version"], ["chrome", "--version"], ["chromium", "--version"], ["chromium-browser", "--version"]):
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
            m = re.search(r'(\d+)\.', out)
            if m:
                return int(m.group(1))
        except Exception:
            continue

    return None

def scrape_chewy(driver):
    url = 'https://www.chewy.com/nulo-freestyle-turkey-chicken-recipe/dp/168510'
    try:
        driver.get(url)
        time.sleep(random.uniform(6.0, 10.0))
        sale_price = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME,"styles_priceNoDeal__JGk8L")))
        if not sale_price:
            logging.warning(f"No price found on Chewy page:")
            return None
        price = sale_price.text.splitlines()[-1].replace('$', '').strip()
        pack_size = "12 cans"
        unit_oz = 12.5
        price_per_oz = (float(price) / 12.0) / unit_oz

        return {
            'company': 'Chewy',
            'price': price,
            'price_per_oz': round(price_per_oz, 2),
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
        time.sleep(random.uniform(6.0, 10.0))
        whole_price = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME,"a-price-whole")))
        fraction_price = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME,"a-price-fraction")))

        if not whole_price or not fraction_price:
            logging.error(f"Failed to scrape from Amazon:")

        price = int(whole_price.text) + (int(fraction_price.text) * .01)
        pack_size = "12 cans"
        unit_oz = 12.5
        price_per_oz = (price / 12) / unit_oz

        return {
            'company': 'Amazon',
            'price': price,
            'price_per_oz': round(price_per_oz, 2),
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
        time.sleep(random.uniform(6.0, 10.0))
        # sale_price = WebDriverWait(driver, 10).until(
        #     EC.presence_of_element_located((By.CLASS_NAME,"purchase-type-selector-styled__PurchaseTypePrice-sc-663c57fc-1")))
        sale_price = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME,"purchase-type-selector-styled__PurchaseTypePrice-sc-7a1b7620-1")))

        discount_elems = driver.find_elements(By.ID, "sale-message-red")
        discount = discount_elems[0] if discount_elems else None

        if not sale_price:
            logging.warning(f"No price found on Petco page:")
            return None
        # parse discount if present (look for "XX%")
        percent_off = None
        if discount:
            discount_text = discount.text
            m = re.search(r'(\d+)%', discount_text)
            if m:
                try:
                    percent_off = int(m.group(1))
                except ValueError:
                    percent_off = None

        if percent_off is not None:
            logging.info(f"Petco discount: {percent_off}%")

        price_clean = float(sale_price.text.replace('$','').strip())
        # apply discount if any
        if percent_off:
            price_clean = price_clean * (100 - percent_off) / 100.0

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
        time.sleep(random.uniform(6.0, 10.0))
        sale_price = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME,"sparky-c-price--sale")))
        og_price = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME,"sparky-c-price")))
        price_str = sale_price.text if sale_price else og_price.text if og_price else None

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
            'price_per_oz': round(price_per_oz, 2),
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


def run_scraper():
    options = uc.ChromeOptions()
    options.add_argument("--incognito")
    options.add_argument(
    "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36")
    # options.add_argument("--headless=new")  # modern headless mode

    driver = None
    url = os.getenv("DATABASE_URL")

    # detect Chrome major version and pass version_main when available
    version_main = get_chrome_major_version()
    try:
        if version_main:
            logging.info(f"Detected Chrome major version: {version_main}")
            driver = uc.Chrome(options=options, version_main=version_main)
        else:
            driver = uc.Chrome(options=options)
    except Exception as e:
        logging.warning(f"Failed creating Chrome with version_main={version_main}: {e}; retrying without version_main")
        driver = uc.Chrome(options=options)

    try:
        pg_conn = connect_with_retry(url)
        with pg_conn.cursor() as pg_cursor:
            for scrape in [scrape_petsmart, scrape_petco, scrape_chewy, scrape_amazon]:
            # for scrape in [scrape_petco]:
                try:
                    record = scrape(driver)
                    if record:
                        insert_price_record(pg_cursor,record)
                        pg_conn.commit()

                except Exception as e:
                    pg_conn.rollback()
                    logging.warning(f"{scrape} failed {e}")

    except psycopg2.OperationalError as e:
        print(f"Error connecting to PostgreSQL: {e}")
        raise

    except Exception as e:
        print(f"Error : {e}")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    run_scraper()
