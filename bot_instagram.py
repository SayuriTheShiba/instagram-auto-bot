import time
import random
import requests
import logging
import sys
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
from bs4 import BeautifulSoup
from celery import Celery
import os

# 🔹 Configurar logging para Railway
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Cargar variables de entorno
INSTAGRAM_USER = os.getenv("INSTAGRAM_USER")
INSTAGRAM_PASS = os.getenv("INSTAGRAM_PASS")
MONGO_URI = os.getenv("MONGO_URL")
REDIS_URL = os.getenv("REDIS_URL")

# Configurar base de datos
client = MongoClient(MONGO_URI)
db = client["instagram_bot"]
posts_collection = db["posts"]

# Configurar Celery
app = Celery("bot_instagram", broker=REDIS_URL)
app.conf.broker_connection_retry_on_startup = True
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1
app.conf.task_reject_on_worker_lost = True

# Obtener proxies gratuitos
def get_free_proxies():
    try:
        url = "https://free-proxy-list.net/"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        proxies = [
            f"http://{row.find_all('td')[0].text.strip()}:{row.find_all('td')[1].text.strip()}"
            for row in soup.select("table tbody tr") if len(row.find_all("td")) >= 7 and row.find_all("td")[6].text.strip().lower() == "yes"
        ]

        if not proxies:
            logging.warning("⚠️ No se encontraron proxies HTTPS.")
        return proxies
    except Exception as e:
        logging.error(f"❌ Error al obtener proxies: {e}")
        return []

proxies = get_free_proxies()

def get_random_proxy():
    return {"http": random.choice(proxies), "https": random.choice(proxies)} if proxies else None

# Configurar Selenium WebDriver
def configure_selenium():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    proxy = get_random_proxy()
    if proxy:
        options.add_argument(f"--proxy-server={proxy['http']}")

    try:
        logging.info("🔄 Iniciando WebDriver para Selenium...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        logging.error(f"❌ Error configurando Selenium: {e}")
        return None

# Iniciar sesión en Instagram
def login_instagram():
    driver = configure_selenium()
    if not driver:
        logging.error("❌ WebDriver no inició correctamente.")
        return None

    logging.info("🔄 Iniciando sesión en Instagram...")
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(random.uniform(3, 7))

    try:
        wait = WebDriverWait(driver, 15)
        username_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']")))
        password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']")))

        username_input.send_keys(INSTAGRAM_USER)
        password_input.send_keys(INSTAGRAM_PASS)
        password_input.send_keys(Keys.RETURN)

        time.sleep(random.uniform(5, 10))
        if "challenge" in driver.current_url or "checkpoint" in driver.current_url:
            logging.warning("⚠️ Instagram requiere verificación manual.")
            driver.quit()
            return None

        logging.info("✅ Inicio de sesión exitoso en Instagram.")
        return driver
    except Exception as e:
        logging.error(f"❌ Error al iniciar sesión: {e}")
        driver.quit()
        return None

# Obtener publicaciones por hashtag
def get_posts_by_hashtag(driver, hashtag):
    try:
        logging.info(f"🔍 Buscando publicaciones para #{hashtag}")
        driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        time.sleep(random.uniform(5, 10))
        return [post.get_attribute("href") for post in driver.find_elements(By.CSS_SELECTOR, "article div div div div a")[:5]]
    except Exception as e:
        logging.error(f"❌ Error al obtener posts de #{hashtag}: {e}")
        return []

# Descargar imagen y obtener autor
def download_image(driver, post_url):
    try:
        logging.info(f"📥 Descargando imagen desde {post_url}")
        driver.get(post_url)
        time.sleep(random.uniform(5, 10))
        image_element = driver.find_element(By.CSS_SELECTOR, "article img")
        image_url = image_element.get_attribute("src")

        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        img.save("post.jpg")

        author_element = driver.find_element(By.CSS_SELECTOR, "header div div div span a")
        return author_element.text
    except Exception as e:
        logging.error(f"❌ Error al descargar imagen: {e}")
        return "Unknown"

# Publicar en Instagram
def post_image(driver, image_path, caption):
    try:
        logging.info("🚀 Publicando en Instagram...")
        driver.get("https://www.instagram.com/")
        time.sleep(random.uniform(5, 10))
        driver.find_element(By.XPATH, "//div[text()='Create']").click()
        time.sleep(random.uniform(3, 7))

        file_input = driver.find_element(By.XPATH, "//input[@type='file']")
        file_input.send_keys(image_path)
        time.sleep(random.uniform(3, 7))

        driver.find_element(By.XPATH, "//button[text()='Next']").click()
        time.sleep(random.uniform(3, 7))

        caption_box = driver.find_element(By.XPATH, "//textarea")
        caption_box.send_keys(caption)

        driver.find_element(By.XPATH, "//button[text()='Share']").click()
        time.sleep(random.uniform(5, 10))

        logging.info("✅ Publicación exitosa.")
    except Exception as e:
        logging.error(f"❌ Error al publicar: {e}")

# Automatización total
@app.task
def automate_instagram():
    driver = login_instagram()
    if driver is None:
        logging.warning("⚠️ Tarea detenida: Error de inicio de sesión.")
        return

    hashtags = ["sofubi", "arttoy", "designerart"]
    seo_captions = [
        "🔥 Descubre esta joya del #Sofubi 🎨 ¿Qué te parece? 🚀\n#ArtToy #KaijuArt",
        "✨ Este #ArtToy es una obra maestra 🏆\n🎨 Creado por @{author}, un maestro del #Sofubi 👀",
    ]

    for hashtag in hashtags:
        posts = get_posts_by_hashtag(driver, hashtag)
        for post in posts:
            author = download_image(driver, post)
            caption = random.choice(seo_captions).replace("@{author}", f"@{author}")
            post_image(driver, "post.jpg", caption)
            time.sleep(random.uniform(1800, 3600))

    logging.info("✅ Tarea completada. Siguiente ejecución en 1 hora.")
    driver.quit()

if __name__ == "__main__":
    automate_instagram.apply_async(countdown=3600)

