from re import search

from dynaconf import Dynaconf
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from requests import get
from uvicorn import run

settings = Dynaconf(settings_files=["static/settings.yaml", "static/icons.yaml"])

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/icons", StaticFiles(directory="static/icons"), name="icons")
templates = Jinja2Templates(directory="static/templates")


# ---- Functions


def https_url_for(request: Request, name, **path_params):
    http_url = request.url_for(name, **path_params)
    return http_url.replace("http", "http", 1)


def get_location(ip_address):
    response = get(f"https://ipapi.co/{ip_address}/json/").json()
    location = [response.get(key, "") for key in ("city", "region", "country_name")]
    return " | ".join(loc for loc in location if loc)


# ---- App

templates.env.globals["https_url_for"] = https_url_for


@app.get("/", response_class=HTMLResponse)
def ip_page(request: Request):
    ip = request.client.host
    location = get_location(ip)
    user_agent = request.headers.get("user-agent")
    device, os = search(r"\s\((.+?)\)\s", user_agent).group(1).split("; ")[:2]
    browser = search(r"(.+)\/", user_agent.split(" ")[-1]).group(1)
    # log in file
    with open("ips.csv", "a+") as file:
        file.write(f"{ip},{location},{device},{os},{browser}\n")
    # log on Telegram
    if settings.telegram.token:
        loc = location or "unknown"
        params = {
            "chat_id": settings.telegram.chat,
            "text": f"📱 *{device}* ({os}) on *{browser}*\n⚙️ `{ip}`\n📍 _{loc}_",
            "parse_mode": "Markdown",
        }
        try:
            get(
                f"https://api.telegram.org/bot{settings.telegram.token}/sendMessage",
                params=params,
            )
        except Exception as e:
            raise e
            print("Ops! Something went wrong with Telegram logging")
    return templates.TemplateResponse(
        "ip.html",
        {
            "request": request,
            "location": location,
            "device": device,
            "os": os,
            "browser": browser,
        },
    )


if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8242)
