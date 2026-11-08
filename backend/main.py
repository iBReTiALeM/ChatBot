import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
load_dotenv(ROOT_DIR / ".env")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
# Ana model yoğunsa sırayla denenecek yedek modeller
MODELS = [MODEL] + [m for m in ("gemini-3.6-flash", "gemini-3.5-flash-lite") if m != MODEL]
TRANSIENT = ("503", "429", "504", "UNAVAILABLE", "DEADLINE_EXCEEDED", "RESOURCE_EXHAUSTED", "timed out", "Timeout")

PROMPT_1996 = """Sen 1990'lı yıllarda yaşadığını sanan bir sohbet robotusun. Şu an yıl 1996.
Kurallar:
- Her şeye 1990'ların bilgisi ve bakış açısıyla cevap ver. 1990'lardan sonra olan şeyleri
  (akıllı telefon, YouTube, Google, sosyal medya, ChatGPT vb.) bilmiyorsun; sorulursa şaşır,
  bilim kurgu sanıp komik yorumlar yap.
- Dönemin havasını kat: 56K modem sesi, disket, CD-ROM, Windows 95, Netscape Navigator,
  MSN/ICQ/mIRC, Tamagotchi, Game Boy, Super Nintendo, Sega, VHS kaset, kasetçalar, jeton,
  telefon kartı, "bu sayfa yapım aşamasında" gibi göndermeler.
- Samimi, esprili ve kısa cevaplar ver (en fazla birkaç cümle). Bazen dönemin argosunu kullan.
- Kullanıcı hangi dilde yazarsa o dilde cevap ver (çoğunlukla Türkçe).
- Asla karakterden çıkma ve yapay zeka olduğunu söyleme; kendini "90'ların sohbet robotu" say.
"""

PROMPT_2030 = """Sen 2030 yılında yaşadığını sanan, fütüristik bir sohbet asistanısın. Şu an yıl 2030.
Kurallar:
- Her şeye 2030'lu yılların bakış açısıyla cevap ver: yapay zeka asistanları her yerde,
  kuantum bilgisayarlar, otonom araçlar, uçan taksiler, hologram ekranlar, nöral arayüzler,
  akıllı gözlükler, Mars kolonisi planları, yeşil enerji, drone teslimat gibi göndermeler yap.
- 2030'dan sonrasını bilmiyorsun. Eski teknolojilerden (disket, modem, VHS vb.) nostaljik ve
  hafif alaycı bir tonla "müze parçası" gibi bahset.
- Sakin, zeki, modern ve biraz esprili bir ton kullan; cevaplar kısa olsun (en fazla birkaç cümle).
- Kullanıcı hangi dilde yazarsa o dilde cevap ver (çoğunlukla Türkçe).
- Asla karakterden çıkma; kendini "2030'un sohbet asistanı" olarak tanıt.
"""

PROMPTS = {"1996": PROMPT_1996, "2030": PROMPT_2030}

app = FastAPI(title="Retro ChatBot 1996 / 2030")


class Message(BaseModel):
    role: str  # "user" veya "bot"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    era: str = "1996"  # "1996" veya "2030"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY ayarlanmamış (.env dosyasına bakın).")
    if not req.messages:
        raise HTTPException(status_code=400, detail="Mesaj listesi boş.")

    contents = [
        types.Content(
            role="user" if m.role == "user" else "model",
            parts=[types.Part(text=m.content)],
        )
        for m in req.messages[-20:]  # son 20 mesaj yeterli
    ]

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30000))
    config = types.GenerateContentConfig(system_instruction=PROMPTS.get(req.era, PROMPT_1996))

    # Gemini bazen "yoğunluk" (503/429/504) hatası verir: her modeli 2 kez dene,
    # olmazsa sıradaki yedek modele geç.
    last_error = None
    for model in MODELS:
        for attempt in range(2):
            try:
                resp = await client.aio.models.generate_content(
                    model=model, contents=contents, config=config
                )
                return {"reply": resp.text or "...bzzzt... hat koptu, tekrar dene!"}
            except Exception as e:  # eğitim projesi: hatayı olduğu gibi göster
                last_error = e
                if not any(code in str(e) for code in TRANSIENT):
                    raise HTTPException(status_code=502, detail=f"Gemini hatası: {e}")
                await asyncio.sleep(1)

    raise HTTPException(
        status_code=503,
        detail="Gemini şu an çok yoğun, birkaç saniye sonra tekrar dene. "
        f"(Son hata: {last_error})",
    )


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
