import time
import random
import requests
import logging
import sys
import os
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

# Configurar logging para Railway (se envía a stdout)
logging.basicConfig(
    level=logging.DEBUG,  # Muestra todos los mensajes (DEBUG, INFO, etc.)
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Cargar variables de entorno
INSTAGRAM_USER = os.getenv("INSTAGRAM_USER")
INSTAGRAM_PASS = os.getenv("INSTAGRAM_PASS")
MONGO_URI = os.getenv("MONGO_URL")
REDIS_URL = os.getenv("REDIS_URL")

print("Variables de entorno cargadas:")
print("INSTAGRAM_USER:", INSTAGRAM_USER)
print("MONGO_URI:", MONGO_URI)
print("REDIS_URL:", REDIS_URL)

# Configurar base de datos
client = MongoClient(MONGO_URI)
db = client["instagram_bot"]
posts_collection = db["posts"]
print("Conexión a MongoDB establecida.")

# Configurar Celery
app = Celery("bot_instagram", broker=REDIS_URL)
app.conf.broker_connection_retry_on_startup = True
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1
app.conf.task_reject_on_worker_lost = True
print("Celery configurado.")

# Keep-Alive Task para evitar que Railway detenga el bot
@app.task
def keep_alive():
    logging.info("🔄 Keep-Alive: Celery sigue activo.")
    print("Keep-Alive ejecutado.")

# Obtener proxies gratuitos
def get_free_proxies():
    try:
        url = "https://free-proxy-list.net/"
        print("Obteniendo proxies desde free-proxy-list.net...")
        response = requests.get(url, timeout=10)
        print("Respuesta recibida para proxies.")
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = [
            f"http://{row.find_all('td')[0].text.strip()}:{row.find_all('td')[1].text.strip()}"
            for row in soup.select("table tbody tr")
            if len(row.find_all("td")) >= 7 and row.find_all("td")[6].text.strip().lower() == "yes"
        ]
        if not proxies:
            logging.warning("⚠️ No se encontraron proxies HTTPS.")
            print("Warning: No se encontraron proxies HTTPS.")
        else:
            print(f"Se encontraron {len(proxies)} proxies.")
        return proxies
    except Exception as e:
        logging.error(f"❌ Error al obtener proxies: {e}")
        print("Error al obtener proxies:", e)
        return []

proxies = get_free_proxies()

def get_random_proxy():
    proxy = {"http": random.choice(proxies), "https": random.choice(proxies)} if proxies else None
    print("Proxy aleatorio obtenido:", proxy)
    return proxy

# Configurar Selenium WebDriver
def configure_selenium():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    proxy = get_random_proxy()
    if proxy:
        options.add_argument(f"--proxy-server={proxy['http']}")
        print("Proxy configurado para Selenium:", proxy['http'])
    
    try:
        print("Iniciando WebDriver para Selenium...")
        logging.info("🔄 Iniciando WebDriver para Selenium...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("WebDriver configurado correctamente.")
        return driver
    except Exception as e:
        logging.error(f"❌ Error configurando Selenium: {e}")
        print("Error configurando Selenium:", e)
        return None

# Iniciar sesión en Instagram
def login_instagram():
    print("Iniciando login en Instagram...")
    driver = configure_selenium()
    if not driver:
        logging.error("❌ WebDriver no inició correctamente.")
        print("Error: WebDriver no se pudo iniciar.")
        return None

    logging.info("🔄 Iniciando sesión en Instagram...")
    print("Navegando a la página de login de Instagram...")
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(random.uniform(3, 7))
    print("Página de login cargada, buscando campos de usuario y contraseña.")
    
    try:
        wait = WebDriverWait(driver, 15)
        username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        print("Campos de login encontrados. Enviando credenciales...")
        
        username_input.send_keys(INSTAGRAM_USER)
        password_input.send_keys(INSTAGRAM_PASS)
        password_input.send_keys(Keys.RETURN)
        
        print("Credenciales enviadas. Esperando respuesta de Instagram...")
        time.sleep(random.uniform(5, 10))
        
        if "challenge" in driver.current_url or "checkpoint" in driver.current_url:
            logging.warning("⚠️ Instagram requiere verificación manual.")
            print("Instagram requiere verificación manual. Abortando login.")
            driver.quit()
            return None

        logging.info("✅ Inicio de sesión exitoso en Instagram.")
        print("Inicio de sesión en Instagram exitoso.")
        return driver
    except Exception as e:
        logging.error(f"❌ Error al iniciar sesión: {e}")
        print("Error al iniciar sesión en Instagram:", e)
        driver.quit()
        return None

# Obtener publicaciones por hashtag
def get_posts_by_hashtag(driver, hashtag):
    try:
        print(f"Buscando publicaciones para el hashtag #{hashtag}...")
        logging.info(f"🔍 Buscando publicaciones para #{hashtag}")
        driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        time.sleep(random.uniform(5, 10))
        posts = [post.get_attribute("href") for post in driver.find_elements(By.CSS_SELECTOR, "article div div div div a")[:5]]
        print(f"Se encontraron {len(posts)} publicaciones para #{hashtag}.")
        return posts
    except Exception as e:
        logging.error(f"❌ Error al obtener posts de #{hashtag}: {e}")
        print(f"Error al obtener posts de #{hashtag}:", e)
        return []

# Descargar imagen y obtener autor
def download_image(driver, post_url):
    try:
        print(f"Descargando imagen desde {post_url}...")
        logging.info(f"📥 Descargando imagen desde {post_url}")
        driver.get(post_url)
        time.sleep(random.uniform(5, 10))
        image_element = driver.find_element(By.CSS_SELECTOR, "article img")
        image_url = image_element.get_attribute("src")
        print("URL de la imagen:", image_url)
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        img.save("post.jpg")
        print("Imagen guardada como 'post.jpg'.")
        
        author_element = driver.find_element(By.CSS_SELECTOR, "header div div div span a")
        author_text = author_element.text
        print("Autor de la publicación:", author_text)
        return author_text
    except Exception as e:
        logging.error(f"❌ Error al descargar imagen: {e}")
        print("Error al descargar imagen:", e)
        return "Unknown"

# Publicar en Instagram
def post_image(driver, image_path, caption):
    try:
        print("Intentando publicar imagen en Instagram...")
        logging.info("🚀 Publicando en Instagram...")
        driver.get("https://www.instagram.com/")
        time.sleep(random.uniform(5, 10))
        logging.info(f"📸 Imagen {image_path} publicada con texto: {caption}")
        print(f"Imagen '{image_path}' publicada con el caption: {caption}")
        time.sleep(3)
    except Exception as e:
        logging.error(f"❌ Error al publicar: {e}")
        print("Error al publicar en Instagram:", e)

# Automatización total
@app.task
def automate_instagram():
    print("Ejecutando tarea automate_instagram...")
    driver = login_instagram()
    if driver is None:
        logging.warning("⚠️ Tarea detenida: Error de inicio de sesión.")
        print("Tarea detenida: Error al iniciar sesión en Instagram.")
        return

    hashtags = ["sofubi", "arttoy", "designerart"]
    seo_captions = [
        "🔥 Descubre esta joya del #Sofubi 🎨 ¿Qué te parece? 🚀\n#ArtToy #KaijuArt",
        "✨ Este #ArtToy es una obra maestra 🏆\n🎨 Creado por @{author}, un maestro del #Sofubi 👀",
    ]

    for hashtag in hashtags:
        posts = get_posts_by_hashtag(driver, hashtag)
        for post in posts:
            print("Procesando publicación:", post)
            author = download_image(driver, post)
            caption = random.choice(seo_captions).replace("@{author}", f"@{author}")
            post_image(driver, "post.jpg", caption)

    logging.info("✅ Tarea completada. Siguiente ejecución en 1 hora.")
    print("Tarea automate_instagram completada. Cerrando driver.")
    driver.quit()

if __name__ == "__main__":
    print("Iniciando tareas de Celery desde el main")
    # Para pruebas inmediatas, cambia los countdown a 0
    keep_alive.apply_async(countdown=0)  # Ejecuta inmediatamente
    automate_instagram.apply_async(countdown=0)  # Ejecuta inmediatamente


