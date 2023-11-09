from datetime import datetime, timedelta
import json
import os
import sqlite3
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] ='1'
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, redirect, request,url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user
)
from oauthlib.oauth2 import WebApplicationClient
import requests

from db import init_db_command
from user import User

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.unauthorized_handler
def unauthorized():
    return "You must login"
try:
    init_db_command()
except sqlite3.OperationalError:
    pass

client = WebApplicationClient(GOOGLE_CLIENT_ID)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)
@app.route("/")
def index():
    if current_user.is_authenticated:
        indian_time = get_current_indian_time()
        return (
            f"<p>Hello, {current_user.name}! You're logged in! Email: {current_user.email}</p>"
            f"<p>Indian Time: {indian_time}</p>"
            "<div><p>Google Profile Picture:</p>"
            f'<img src="{current_user.profile_pic}" alt="Google profile pic"></img></div>'
            '<a class="button" href="/logout">Logout</a>'
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'

@app.route("/login")
def login():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg['authorization_endpoint']
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri= "http://127.0.0.1:5000/login/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)
@app.route("/login/callback")
def callback():
    code = request.args.get("code")
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    print(userinfo_response.json())

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "Email not available or not verified", 400

    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )

    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    login_user(user)
    return redirect(url_for('index'))
def get_current_indian_time():
    now = datetime.utcnow()
    indian_time = now + timedelta(hours=5, minutes=30)
    return indian_time.strftime('%Y-%m-%d %H:%M:%S')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))
def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()
if __name__ == "__main__":
    app.run(debug=True)


