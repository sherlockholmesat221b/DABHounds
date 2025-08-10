# core/auth.py  
  
import requests  
import json  
import os  
  
CONFIG_PATH = "config.json"  
USER_AGENT = (  
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "  
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1337.0.0.0 Safari/537.36"  
)  
  
def load_config():  
    if not os.path.exists(CONFIG_PATH):  
        return {}  
    try:  
        with open(CONFIG_PATH, "r") as f:  
            return json.load(f)  
    except Exception as e:  
        print(f"[DABHound] Failed to read config.json: {e}")  
        return {}  
  
def save_config(config):  
    try:  
        with open(CONFIG_PATH, "w") as f:  
            json.dump(config, f, indent=4)  
        print("[DABHound] Config saved.")  
    except Exception as e:  
        print(f"[DABHound] Failed to save config.json: {e}")  
  
def verify_token(token: str) -> bool:  
    headers = {  
        "Authorization": f"Bearer {token}",  
        "User-Agent": USER_AGENT  
    }  
    try:  
        resp = requests.get("https://dab.yeet.su/api/auth/me", headers=headers)  
        return resp.status_code == 200  
    except requests.RequestException:  
        return False  
  
def login(email: str, password: str) -> str | None:  
    print("[DABHound] Logging in to DAB...")  
    session = requests.Session()  
    headers = {  
        "User-Agent": USER_AGENT,  
        "Content-Type": "application/json"  
    }  
  
    try:  
        response = session.post("https://dab.yeet.su/api/auth/login", json={  
            "email": email,  
            "password": password  
        }, headers=headers)  
    except requests.RequestException as e:  
        print(f"[DABHound] Login failed: {e}")  
        return None  
  
    if response.status_code == 200 and "session" in session.cookies:  
        token = session.cookies.get("session")  
        config = load_config()  
        config["DAB_AUTH_TOKEN"] = token  
        config["DAB_EMAIL"] = email  
        config["DAB_PASSWORD"] = password  
        save_config(config)  
        print("[DABHound] Login successful. Token saved.")  
        return token  
    else:  
        print("[DABHound] Login failed. Check email/password.")  
        print("Status code:", response.status_code)  
        print("Response:", response.text)  
        return None  
  
def ensure_logged_in() -> str:  
    config = load_config()  
    token = config.get("DAB_AUTH_TOKEN")  
  
    if token and verify_token(token):  
        return token  
  
    print("[DABHound] Token is missing or expired. Re-authenticating...")  
  
    email = config.get("DAB_EMAIL")  
    password = config.get("DAB_PASSWORD")  
  
    if email and password:  
        token = login(email, password)  
        if token:  
            return token  
        else:  
            print("[DABHound] Auto-login failed. Please run: dabhounds.py --login")  
            exit(1)  
    else:  
        print("[DABHound] No email/password found in config.json. Please run: dabhounds.py --login")  
        exit(1)  
  
def get_authenticated_session() -> requests.Session:  
    token = ensure_logged_in()  
    session = requests.Session()  
    session.cookies.set("session", token)  
    session.headers.update({  
        "User-Agent": USER_AGENT  
    })  
    return session  
  
def logout():  
    config = load_config()  
    config.pop("DAB_AUTH_TOKEN", None)  
    config.pop("DAB_EMAIL", None)  
    config.pop("DAB_PASSWORD", None)  
    save_config(config)  
    print("[DABHound] Logged out from DAB.")