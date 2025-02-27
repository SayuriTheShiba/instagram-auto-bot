import os
import requests
from flask import Flask, request, redirect

app = Flask(__name__)

# Variables de entorno que configuraremos en Railway
IG_APP_ID = os.getenv("IG_APP_ID")
IG_APP_SECRET = os.getenv("IG_APP_SECRET")
IG_REDIRECT_URI = os.getenv("IG_REDIRECT_URI", "http://localhost:5000/instagram/callback")

@app.route("/")
def index():
    return "¡Hola! Esta es la app del Instagram Auto Bot usando la API oficial."

@app.route("/login")
def login():
    """
    Inicia el flujo OAuth. Redirige al usuario a la página de autorización de Instagram.
    """
    # Para la Instagram Basic Display API
    auth_url = (
        "https://api.instagram.com/oauth/authorize"
        f"?client_id={IG_APP_ID}"
        f"&redirect_uri={IG_REDIRECT_URI}"
        "&scope=user_profile,user_media"  # Ajusta los scopes que necesites
        "&response_type=code"
    )
    return redirect(auth_url)

@app.route("/instagram/callback")
def ig_callback():
    """
    Instagram redirige aquí después de que el usuario autoriza.
    Intercambiamos el 'code' por un 'access_token'.
    """
    code = request.args.get("code")
    if not code:
        return "Error: No se recibió el parámetro 'code' en la callback."

    # Intercambiar 'code' por 'access_token'
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
        # Ejemplo: Obtener info de usuario con el access_token
        user_info = get_user_profile(access_token)
        return (
            f"Autenticación exitosa.<br>"
            f"Access Token: {access_token}<br>"
            f"User ID: {user_id}<br>"
            f"Nombre de Usuario: {user_info.get('username')}<br>"
        )
    else:
        return f"Error al intercambiar code por token: {r.text}"

def get_user_profile(access_token):
    """
    Ejemplo de cómo usar el token para obtener información del usuario.
    """
    url = f"https://graph.instagram.com/me"
    params = {
        "fields": "id,username",
        "access_token": access_token
    }
    resp = requests.get(url, params=params)
    return resp.json()

if __name__ == "__main__":
    # Ejecutar en local con: python app.py
    # En Railway, usará la variable PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

