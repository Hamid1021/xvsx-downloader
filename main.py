import os
import time
import requests

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from downloader import download_ts


app = FastAPI()

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_KEY = os.environ["API_KEY"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


class DownloadRequest(BaseModel):
    playlist_url: str
    chat_id: int
    quality: str


@app.get("/")
def home():
    return {"status": "online"}


@app.post("/download")
def download(
    data: DownloadRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401)

    file_path = None
    file_message_id = None
    notice_message_id = None

    try:
        file_path = download_ts(data.playlist_url)

        if os.path.getsize(file_path) > 50 * 1024 * 1024:
            raise Exception("File exceeds Telegram Bot API limit (50 MB).")

        with open(file_path, "rb") as video:
            response = requests.post(
                f"{TELEGRAM_API}/sendDocument",
                data={"chat_id": data.chat_id},
                files={"document": (
                    f"video_{data.quality}.ts",
                    video,
                    "video/mp2t"
                )},
                timeout=180
            )

        result = response.json()

        if not result.get("ok"):
            raise Exception(result.get("description", "Telegram upload failed"))

        file_message_id = result["result"]["message_id"]

        notice = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": data.chat_id,
                "text": (
                    "⏳ این فایل تا ۲۰ ثانیه دیگر حذف خواهد شد.\n"
                    "لطفاً آن را به Saved Messages منتقل کنید."
                )
            },
            timeout=30
        ).json()

        if notice.get("ok"):
            notice_message_id = notice["result"]["message_id"]

        time.sleep(20)

        for message_id in (file_message_id, notice_message_id):
            if message_id:
                requests.post(
                    f"{TELEGRAM_API}/deleteMessage",
                    json={
                        "chat_id": data.chat_id,
                        "message_id": message_id
                    },
                    timeout=30
                )

        return {"status": "completed"}

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
