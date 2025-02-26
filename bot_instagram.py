import time
import random
import requests
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
from bs4 import BeautifulSoup
from celery import Celery
import os

# Cargar variables de entorno
INSTAGRAM_USER = os.getenv("INSTAGRAM_USER")
INSTAGRAM_PASS = os.getenv("INSTAGRAM_PASS")
MONGO_URI = os.getenv("MONGO_URI")
REDIS_URL = os.getenv("REDIS_URL")

# Configurar base de datos
client = MongoClient(MONGO_URI)
db = client["instagram_bot"]
posts_collection = db["posts"]

# Configurar Celery para tareas automáticas
app = Celery("tasks", broker=REDIS_URL)
app.conf.broker_connection_retry_on_startup = True  # Solución para Celery 6.0

# Obtener proxies gratuitos
def get_free_proxies():
    url = "https://free-proxy-list.net/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    proxies = []
    for row in soup.select("table tbody tr"):
        columns = row.find_all("td")
        if len(columns) >= 7:
            ip, port, https = columns[0].text.strip(), columns[1].text.strip(), columns[6].text.strip()
            if https.lower() == "yes":
                proxies.append(f"http://{ip}:{port}")

    return proxies

# Fuente alternativa de proxies
def get_backup_proxies():
    url = "https://proxylist.geonode.com/api/proxy-list?limit=20&page=1&sort_by=lastChecked&sort_type=desc"
    response = requests.get(url).json()

    proxy_list = []
    for proxy in response["data"]:
        if proxy["protocols"][0] == "https":
            proxy_list.append(f"http://{proxy['ip']}:{proxy['port']}")

    return proxy_list

# Obtener proxies seguros
proxies = get_free_proxies()
if not proxies:
    print("⚠️ No se encontraron proxies en la primera fuente. Probando otra fuente...")
    proxies = get_backup_proxies()

def get_random_proxy():
    if not proxies:
        print("⚠️ No hay proxies disponibles, ejecutando sin proxy.")
        return None
    proxy = random.choice(proxies)
    return {"http": proxy, "https": proxy}

# Configurar Selenium
def configure_selenium():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    proxy = get_random_proxy()
    if proxy:
        options.add_argument(f"--proxy-server={proxy['http']}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# Iniciar sesión en Instagram
def login_instagram():
    driver = configure_selenium()
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(random.uniform(3, 7))

    try:
        driver.find_element(By.NAME, "username").send_keys(INSTAGRAM_USER)
        driver.find_element(By.NAME, "password").send_keys(INSTAGRAM_PASS)
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        time.sleep(random.uniform(5, 10))
    except Exception as e:
        print(f"❌ Error al iniciar sesión: {e}")
        driver.quit()

    return driver

# Obtener publicaciones por hashtag
def get_posts_by_hashtag(driver, hashtag):
    driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
    time.sleep(random.uniform(5, 10))

    posts = driver.find_elements(By.CSS_SELECTOR, "article div div div div a")
    links = [post.get_attribute("href") for post in posts[:5]]
    return links

# Descargar imagen y obtener autor
def download_image(driver, post_url):
    driver.get(post_url)
    time.sleep(random.uniform(5, 10))

    try:
        image_element = driver.find_element(By.CSS_SELECTOR, "article img")
        image_url = image_element.get_attribute("src")
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        img.save("post.jpg")

        author_element = driver.find_element(By.CSS_SELECTOR, "header div div div span a")
        author = author_element.text
        return author
    except Exception as e:
        print(f"❌ Error descargando imagen: {e}")
        return None

# Publicar en Instagram
def post_image(driver, image_path, caption):
    driver.get("https://www.instagram.com/")
    time.sleep(random.uniform(5, 10))

    try:
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
    except Exception as e:
        print(f"❌ Error publicando en Instagram: {e}")

# Automatización total
@app.task
def automate_instagram():
    driver = login_instagram()
    hashtags = [
        "sofubi", "arttoy", "designerart", "sofubipromoter", "softvinyl", 
        "sofubiforsale", "sofubilottery", "kaijuart", "handmadearttoy", 
        "arttoycollector", "resinart", "japanesetoys", "vinylart", "urbanvinyl", 
        "lowbrowart", "creativetoys", "hiddengemtoy", "collectibles"
    ]  # Lista ampliada de hashtags

    seo_captions = [
        "🔥 Descubre esta joya del #Sofubi 🎨 Perfecto para coleccionistas exigentes. ¿Qué te parece? 🚀\n#ArtToy #DesignerToys #KaijuArt",
        "✨ Este #ArtToy es una obra maestra 🏆 Ideal para fans del #VinylArt y el #SoftVinyl 🎭\n🎨 Mención especial a @{author} por esta pieza increíble. #HandmadeArtToy",
        "💎 Para los verdaderos coleccionistas: una pieza de ensueño 🤩🔥\n🎨 Creado por @{author}, un maestro del #Sofubi 👀 ¿Ya tienes el tuyo? #RareToy",
        "🚀 Diseño exclusivo para amantes del #UrbanVinyl y el #ResinArt 💀\n🎨 Esta pieza de @{author} es un MUST HAVE para tu colección. #Collectibles",
        "🔥 Edición limitada 🚨 No te quedes sin esta obra de arte en soft vinyl 🖤\n🛒 ¿La agregarías a tu colección? #KaijuArt #ToyPhotography",
        "🎭 El arte en vinil cobra vida con esta impresionante creación 🎨\nCreado por @{author}, una leyenda del #ArtToy 👏🔥\n📢 #ToyCollector #JapaneseToys",
        "🏆 Solo para coleccionistas serios 😎 Esta pieza de #Sofubi es una rareza absoluta 🛒\n🎨 Obra de @{author}, ¡apoya a los artistas! #VinylToys",
        "🔮 Magia en soft vinyl ✨ Una creación única de @{author} que redefine el #DesignerToys\n🔥 #HandmadeArtToy #HiddenGemToy",
        "🚀 Nuevo hallazgo en la escena del #Sofubi 🔥 ¿Quién más ama estos detalles? 👀\n🎨 By @{author}, una joya del #VinylArt",
        "💀 El #LowbrowArt en su máxima expresión 🎭\n🎨 Obra maestra de @{author} para coleccionistas con ojo crítico 👁️🔥\n#CollectibleVinyl",
    ]  # Lista de captions SEO aleatorios para mayor diversidad

    for hashtag in hashtags:
        posts = get_posts_by_hashtag(driver, hashtag)
        for post in posts:
            author = download_image(driver, post)
            if not author:
                continue  # Evita errores si no pudo descargar la imagen

            seo_caption = random.choice(seo_captions).replace("@{author}", f"@{author}")
            post_image(driver, "post.jpg", seo_caption)

            time.sleep(random.uniform(1800, 3600))

automate_instagram.apply_async(countdown=3600)  # Ejecutar cada hora
