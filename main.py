#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# =================================================
# CONFIGURAÇÕES GERAIS
# =================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
STATE_FILE = os.path.join(BASE_DIR, ".last_sent")

TZ_BRASILIA = timezone(timedelta(hours=-3))

ALLOWED_SYMBOLS = {
    "BCHUSDT", "BNBUSDT", "CHZUSDT", "DOGEUSDT", "ENAUSDT",
    "ETHUSDT", "JASMYUSDT", "SOLUSDT", "UNIUSDT", "XMRUSDT", "XRPUSDT"
}

# =================================================
# ENV (local / Railway)
# =================================================

try:
    from dotenv import load_dotenv
    if os.path.exists(".env"):
        load_dotenv()
        print("[ENV] .env carregado (local)")
    else:
        print("[ENV] execução web (Railway)")
except ImportError:
    print("[ENV] python-dotenv ausente")

def get_env(name: str, cast=str, required=True):
    value = os.environ.get(name)
    if required and not value:
        raise RuntimeError(f"Variável de ambiente ausente: {name}")
    return cast(value) if value else None

API_ID = get_env("API_ID", int)
API_HASH = get_env("API_HASH")
SOURCE_CHAT_ID = get_env("SOURCE_CHAT_ID", int)
TARGET_CHAT_ID = get_env("TARGET_CHAT_ID", int)
SESSION_STRING = get_env("TELEGRAM_SESSION_STRING")

# =================================================
# CLIENTE TELEGRAM
# =================================================

client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH
)

target_peer = None  # resolvido no startup

# =================================================
# PARSER DE MENSAGEM
# =================================================

def parse_signal_message(text: str):
    text = text.strip().replace("\r", "")

    pattern = re.compile(
        r'(?P<exchange>\w+):(?P<symbol>\w+).*?'
        r'(?P<signal>compra|venda).*?'
        r'(?P<time>\d+)\s*minutos?.*?'
        r'(Preço:?\s*(?P<price>[\d.,]+))?',
        re.IGNORECASE | re.DOTALL
    )

    match = pattern.search(text)
    if not match:
        return None

    try:
        price = float(match.group("price").replace(",", ".")) if match.group("price") else None
    except ValueError:
        price = None

    return {
        "exchange": match.group("exchange").upper(),
        "symbol": match.group("symbol").upper(),
        "signal": match.group("signal").lower(),
        "timeframe": f"{match.group('time')} minutos",
        "price": price
    }

# =================================================
# LOG
# =================================================

def write_log(data: dict):
    os.makedirs(LOG_DIR, exist_ok=True)
    now = datetime.now(TZ_BRASILIA)

    file_name = f"log_{now.date().isoformat()}.txt"
    log_path = os.path.join(LOG_DIR, file_name)

    header = "Data\tHora\tExchange\tMoeda\tSinal\tGrafico\tPreco\n"
    exists = os.path.exists(log_path)

    with open(log_path, "a", encoding="utf-8") as f:
        if not exists:
            f.write(header)

        f.write(
            f"{now.strftime('%d/%m/%Y')}\t"
            f"{now.strftime('%H:%M:%S')}\t"
            f"{data['exchange']}\t"
            f"{data['symbol']}\t"
            f"{data['signal']}\t"
            f"{data['timeframe']}\t"
            f"{data['price'] if data['price'] is not None else ''}\n"
        )

# =================================================
# LISTENER
# =================================================

@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def forward_message(event):
    try:
        text = event.message.text or ""
        parsed = parse_signal_message(text)

        if not parsed:
            return

        write_log(parsed)
        print(f"[LOG] {parsed}")

        if parsed["symbol"] not in ALLOWED_SYMBOLS:
            print(f"[SKIP] Moeda ignorada: {parsed['symbol']}")
            return

        if event.message.media:
            await client.send_file(
                target_peer,
                event.message.media,
                caption=text
            )
        else:
            await client.send_message(
                target_peer,
                text
            )

        print(f"[FORWARD] Enviado: {parsed['symbol']}")

    except Exception as e:
        print(f"[ERRO] Handler: {e}")

# =================================================
# LOG DIÁRIO
# =================================================

def get_last_sent_date():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return f.read().strip()

def set_last_sent_date(date_str):
    with open(STATE_FILE, "w") as f:
        f.write(date_str)

async def send_daily_log():
    now = datetime.now(TZ_BRASILIA)
    log_date = now.date() - timedelta(days=1)

    file_name = f"log_{log_date.isoformat()}.txt"
    log_path = os.path.join(LOG_DIR, file_name)

    if not os.path.exists(log_path):
        print("[LOG] Nenhum arquivo para envio")
        return

    caption = (
        f"📊 Log diário\n"
        f"Data: {log_date.strftime('%d/%m/%Y')}\n"
        f"Envio: {now.strftime('%H:%M')}"
    )

    await client.send_file(target_peer, log_path, caption=caption)
    set_last_sent_date(log_date.isoformat())
    print("[LOG] Arquivo enviado")

# =================================================
# SCHEDULER
# =================================================

async def scheduler():
    while True:
        now = datetime.now(TZ_BRASILIA)
        last_sent = get_last_sent_date()

        if now.hour == 0 and now.minute == 0:
            if last_sent != now.date().isoformat():
                await send_daily_log()
                await asyncio.sleep(70)

        await asyncio.sleep(15)

# =================================================
# MAIN
# =================================================

async def main():
    global target_peer

    print("Modo BOT: iniciado...")

    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError("Sessão Telegram inválida ou revogada")

    target_peer = await client.get_entity(TARGET_CHAT_ID)
    print("[INIT] Peer de destino resolvido")

    asyncio.create_task(scheduler())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
