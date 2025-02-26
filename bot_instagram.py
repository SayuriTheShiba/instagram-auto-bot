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
MONGO_URI = os.getenv("MONGO_URL")   # Asumimos que en Railway la variable se llama MONGO_URL
REDIS_URL = os.getenv("REDIS_URL")

# Configurar base de datos
client = MongoClient(MONGO_URI)
db = client["instagram_bot"]
posts_collection = db["posts"]

# Configurar Celery para tareas automáticas
app = Celery("tasks", broker=REDIS_URL)

def get_free_proxies():
    url = "https://free-proxy-list.net/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    proxies = []
    for row in soup.select("table tbody tr"):
        columns = row.find_all("td")
        # Validar que haya al menos 7 columnas antes de acceder a ellas
        if len(columns) < 7:
            continue
        ip = columns[0].text.strip()
        port = columns[1].text.strip()
        https = columns[6].text.strip()
        if https.lower() == "yes":
            proxies.append(f"http://{ip}:{port}")

    # Opcional: manejar el caso de que no haya proxies
    if not proxies:
        print("⚠️ No se encontraron proxies HTTPS en la fuente principal.")
    return proxies

proxies = get_free_proxies()

def get_random_proxy():
    if not proxies:
        print("⚠️ No hay proxies disponibles, se usará conexión directa.")
        return None
    proxy = random.choice(proxies)
    return {"http": proxy, "https": proxy}

def configure_selenium():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    random_proxy = get_random_proxy()
    if random_proxy:
        proxy_http = random_proxy["http"]
        options.add_argument(f"--proxy-server={proxy_http}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def login_instagram():
    driver = configure_selenium()
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(random.uniform(3, 7))

    try:
        driver.find_element(By.NAME, "username").send_keys(INSTAGRAM_USER)
        driver.find_element(By.NAME, "password").send_keys(INSTAGRAM_PASS)
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)

        time.sleep(random.uniform(5, 10))

        current_url = driver.current_url
        if "challenge" in current_url or "checkpoint" in current_url:
            print("⚠️ Instagram está pidiendo verificación (challenge/checkpoint). Revisa la cuenta manualmente.")
            return None
        
        print("✅ Inicio de sesión exitoso en Instagram.")
    except Exception as e:
        print(f"❌ Error al iniciar sesión en Instagram: {e}")
        driver.quit()
        return None

    return driver

def get_posts_by_hashtag(driver, hashtag):
    driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
    time.sleep(random.uniform(5, 10))

    posts = driver.find_elements(By.CSS_SELECTOR, "article div div div div a")
    links = [post.get_attribute("href") for post in posts[:5]]  # Extrae 5 para evitar bloqueos
    return links

def download_image(driver, post_url):
    driver.get(post_url)
    time.sleep(random.uniform(5, 10))

    image_element = driver.find_element(By.CSS_SELECTOR, "article img")
    image_url = image_element.get_attribute("src")

    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    img.save("post.jpg")

    author_element = driver.find_element(By.CSS_SELECTOR, "header div div div span a")
    author = author_element.text
    return author

def post_image(driver, image_path, caption):
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

@app.task
def automate_instagram():
    driver = login_instagram()
    if driver is None:
        print("⚠️ No se pudo iniciar sesión. Tarea terminada.")
        return

    hashtags = [
        "sofubi", "arttoy", "designerart", "sofubipromoter", "softvinyl", 
        "sofubiforsale", "sofubilottery", "kaijuart", "handmadearttoy", 
        "arttoycollector", "resinart", "japanesetoys", "vinylart", "urbanvinyl", 
        "lowbrowart", "creativetoys", "hiddengemtoy", "collectibles"
    ]

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
    ]

    for hashtag in hashtags:
        posts = get_posts_by_hashtag(driver, hashtag)
        for post in posts:
            author = download_image(driver, post)
            final_caption = random.choice(seo_captions).replace("@{author}", f"@{author}")
            post_image(driver, "post.jpg", final_caption)

            # Esperar entre 30 y 60 minutos
            time.sleep(random.uniform(1800, 3600))

automate_instagram.apply_async(countdown=3600)


