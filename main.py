import json
import logging
import random
import re
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (WebDriverException, 
                                        TimeoutException, 
                                        NoSuchElementException)
from fake_useragent import UserAgent

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Product:
    id: int
    name: str
    url: str
    price: int
    category_id: int
    category_url: str
    per_kg: bool = False
    sku: str = None

class Scraper(ABC):
    @abstractmethod
    def init(self):
        pass
    
    @abstractmethod
    def fetch(self, callback):
        pass

class RetailScraper(Scraper):
    BASE_URL = "http://www.superseis.com.py"
    CATEGORY_SELECTOR = "a[href*='/category/']"
    PRODUCT_SELECTOR = ".product-item"
    PAGER_SELECTOR = ".product-pager-box"
    NEXT_PAGE_TEXT = "Siguiente"
    
    def __init__(self, start_url=None):
        self.start_url = start_url or self.BASE_URL
        self.driver = None
        self.categories = {}
        self.product_id_re = re.compile(r"/products/(\d+)-")
        self.category_id_re = re.compile(r"/category/(\d+)-")
        
    def init(self):
        options = webdriver.ChromeOptions()
        #options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        ua = UserAgent()
        options.add_argument(f"user-agent={ua.random}")
        
        self.driver = webdriver.Chrome(options=options)
        try:
            self.driver.get(self.start_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.CATEGORY_SELECTOR))
            )
        except WebDriverException as e:
            logger.error(f"Error inicializando navegador: {str(e)}")
            raise

    def _get_category_id(self, url):
        match = self.category_id_re.search(url)
        if not match:
            raise ValueError(f"No se pudo obtener category_id de {url}")
        return int(match.group(1))
    
    def _get_product_id(self, url):
        match = self.product_id_re.search(url)
        if not match:
            raise ValueError(f"No se pudo obtener product_id de {url}")
        return int(match.group(1))
    
    def _get_price(self, price_element):
        try:
            price_text = price_element.text.strip()
            cleaned_price = price_text.replace(".", "").replace(" ", "").replace("₲", "")
            return int(cleaned_price)
        except (ValueError, AttributeError) as e:
            logger.error(f"Error procesando precio: {str(e)}")
            raise
    
    def _get_sku(self, product_url):
        original_window = self.driver.current_window_handle
        new_tab_opened = False
        try:
            # Abrir nueva pestaña
            self.driver.execute_script("window.open('');")
            new_tab_opened = True
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(product_url)
            
            # Esperar y obtener SKU
            sku_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".sku"))
            )
            sku_text = sku_element.text.strip()
            
            if "Código de Barras:" in sku_text:
                return sku_text.split(":")[1].strip()
            return None
        except TimeoutException:
            logger.warning(f"Timeout obteniendo SKU: {product_url}")
            return None
        except Exception as e:
            logger.warning(f"Error obteniendo SKU: {str(e)}")
            return None
        finally:
            # Cerrar pestaña y volver al contexto original
            if new_tab_opened:
                self.driver.close()
                self.driver.switch_to.window(original_window)
    
    def _process_product(self, element, category_id, category_url, callback):
        try:
            title_element = element.find_element(By.CSS_SELECTOR, ".product-title a")
            price_element = element.find_element(By.CSS_SELECTOR, ".price-label")
            link_element = element.find_element(By.CSS_SELECTOR, ".product-title-link")
            
            product_url = link_element.get_attribute("href")
            product_id = self._get_product_id(product_url)
            price = self._get_price(price_element)
            
            product = Product(
                id=product_id,
                name=title_element.text.strip(),
                url=product_url,
                price=price,
                category_id=category_id,
                category_url=category_url
            )

            # Obtener SKU si es posible en segundo plano
            product.sku = self._get_sku(product_url)
            
            callback(product)
            
        except Exception as e:
            logger.error(f"Elemento: {element}")
            logger.error(f"URL: {category_url}")
            logger.error(f"Category ID: {category_id}")
            logger.error(f"Error procesando producto: {str(e)}")
    
    def _process_category(self, category_url):
        try:
            self.driver.get(category_url)
            category_id = self._get_category_id(category_url)
            self.categories[category_id] = category_url
            
            while True:
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.PRODUCT_SELECTOR)))
                    
                    # Procesar productos
                    products = self.driver.find_elements(By.CSS_SELECTOR, self.PRODUCT_SELECTOR)
                    for product_element in products:
                        yield product_element
                    
                    # Manejar paginación
                    try:
                        pager = self.driver.find_element(By.CSS_SELECTOR, self.PAGER_SELECTOR)
                        next_btn = pager.find_element(By.XPATH, f".//*[contains(text(), '{self.NEXT_PAGE_TEXT}')]")
                        next_btn.click()
                        
                        WebDriverWait(self.driver, 15).until(
                            EC.staleness_of(pager))
                        time.sleep(2)  # Espera corta para estabilización
                    except NoSuchElementException:
                        break  # No hay más páginas
                        
                except TimeoutException:
                    logger.warning("Timeout al cargar productos")
                    self.driver.refresh()
                    time.sleep(3)
                    #maximo 3 intentos
                    for i in range(3):
                        try:
                            WebDriverWait(self.driver, 15).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.PRODUCT_SELECTOR)))
                            break
                        except TimeoutException:
                            logger.warning("Timeout al cargar productos, reintentando...")
                            self.driver.refresh()
                            time.sleep(3)
                    else:
                        logger.error("No se pudo cargar productos")
                        break
                    
        except Exception as e:
            logger.error(f"Error crítico en categoría {category_url}: {str(e)}")
            raise

    def fetch(self, callback):
        try:
            # Obtener URLs de categorías primero
            main_page = self.driver.current_window_handle
            categories = self.driver.find_elements(By.CSS_SELECTOR, self.CATEGORY_SELECTOR)
            category_urls = [cat.get_attribute("href") for cat in categories if cat.get_attribute("href")]
            
            logger.info(f"Encontradas {len(category_urls)} categorías para procesar")
            
            for category_url in category_urls:
                try:
                    logger.info(f"Procesando categoría: {category_url}")
                    for product_element in self._process_category(category_url):
                        self._process_product(
                            product_element,
                            self._get_category_id(category_url),
                            category_url,
                            callback
                        )
                    # Regresar a página principal para evitar problemas de estado
                    self.driver.get(self.start_url)
                    
                except Exception as e:
                    logger.error(f"Error procesando categoría {category_url}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fatal en fetch: {str(e)}")
            raise
        finally:
            self.driver.quit()

def main():
    if len(sys.argv) < 3:
        print("Uso: python scraper.py <scraper_id> <output_file>")
        sys.exit(1)
    
    scraper_id = sys.argv[1]
    output_file = sys.argv[2]
    
    scrapers = {
        "s6": RetailScraper("http://www.superseis.com.py/default.aspx"),
        "stock": RetailScraper("http://www.stock.com.py/default.aspx"),
    }
    
    scraper = scrapers.get(scraper_id)
    if not scraper:
        raise ValueError(f"Scraper inválido: {scraper_id}")
    
    try:
        scraper.init()
    except Exception as e:
        logger.error(f"Error inicializando scraper: {str(e)}")
        sys.exit(1)
    
    with open(output_file, "w", encoding="utf-8") as f:
        def callback(product):
            product_json = json.dumps(product.__dict__, ensure_ascii=False)
            logger.debug(f"Producto obtenido: {product_json}")
            f.write(product_json + "\n")
        
        scraper.fetch(callback)

if __name__ == "__main__":
    main()