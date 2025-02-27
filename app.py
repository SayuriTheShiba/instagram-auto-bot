import os
import requests
from flask import Flask, request, redirect

app = Flask(__name__)

# Obtener las variables de entorno y verificar que estén definidas
IG_APP_ID = os.getenv("IG_APP_ID")
IG_APP_SECRET = os.getenv("IG_APP_SECRET")
IG_REDIRECT_URI = os.getenv("IG_REDIRECT_URI", "http://localhost:5000/instagram/callback")

if not IG_APP_ID or not IG_APP_SECRET:
    raise Exception("Error: Las variables de entorno IG_APP_ID y/o IG_APP_SECRET no están definidas.")

@app.route("/")
def index():
    return "¡Hola! Esta es la app del Instagram Auto Bot usando la API oficial."

@app.route("/login")
def login():
    """
    Inicia el flujo OAuth redirigiendo al usuario a la página de autorización de Instagram.
    """
    auth_url = (
        "https://api.instagram.com/oauth/authorize"
        f"?client_id={IG_APP_ID}"
        f"&redirect_uri={IG_REDIRECT_URI}"
        "&scope=user_profile,user_media"  # Ajusta los scopes necesarios
        "&response_type=code"
    )
    return redirect(auth_url)

@app.route("/instagram/callback")
def ig_callback():
    """
    Esta ruta recibe el 'code' de Instagram tras la autorización y lo intercambia por un access token.
    """
    code = request.args.get("code")
    if not code:
        return "Error: No se recibió el parámetro 'code' en la callback.", 400

    token_url = "https://api.instagram.com/oauth/access_token"
    data = {
        "client_id": IG_APP_ID,
        "client_secret": IG_APP_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": IG_REDIRECT_URI,
        "code": code
    }
    r = requests.post(token_url, data=data)
    if r.status_code == 200:
        token_info = r.json()
        access_token = token_info.get("access_token")
        user_id = token_info.get("user_id")
        # Obtener información del usuario usando el access token
        user_info = get_user_profile(access_token)
        return (
            f"Autenticación exitosa.<br>"
            f"Access Token: {access_token}<br>"
            f"User ID: {user_id}<br>"
            f"Nombre de Usuario: {user_info.get('username', 'No disponible')}<br>"
        )
    else:
        return f"Error al intercambiar code por token: {r.text}", r.status_code

def get_user_profile(access_token):
    """
    Utiliza el access token para obtener información básica del usuario.
    """
    url = "https://graph.instagram.com/me"
    params = {
        "fields": "id,username",
        "access_token": access_token
    }
    resp = requests.get(url, params=params)
    return resp.json()

if __name__ == "__main__":
    # En Railway se usará la variable PORT; en local, usa el puerto 5000 por defecto.
    port = int(os.environ.get("PORT", 5000))
    # En producción se recomienda desactivar debug y usar un servidor WSGI (por ejemplo, Gunicorn)
    app.run(host="0.0.0.0", port=port, debug=True)

