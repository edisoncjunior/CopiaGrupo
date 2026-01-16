# VERSAO 1 - FUNCIONA LOCAL e WEB - Com LOG e envio diário as 9h e 21h

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, events
from telethon.sessions import StringSession

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")

SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")
 
# -------------------------------------------------
# Ambiente local → carrega .env (se existir)
# Ambiente web  → ignora .env e usa env vars
# -------------------------------------------------
try:
    from dotenv import load_dotenv
    if os.path.exists(".env"):
        load_dotenv()
        print("[ENV] .env carregado (execução local)")
    else:
        print("[ENV] execução web (Railway)")
except ImportError:
    # python-dotenv não instalado (Railway/GitHub)
    print("[ENV] python-dotenv ausente (execução web)")

# -------------------------------------------------
# Variáveis de ambiente (obrigatórias)
# -------------------------------------------------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SOURCE_CHAT_ID = int(os.environ["SOURCE_CHAT_ID"])
TARGET_CHAT_ID = int(os.environ["TARGET_CHAT_ID"])
SESSION_STRING = os.environ["TELEGRAM_SESSION_STRING"]

MODE = os.getenv("MODE", "BOT") #versão web

# Nome da sessão (opcional)
SESSION_NAME = "/app/session_forwarder"

# -------------------------------------------------
# Cliente Telegram
# -------------------------------------------------
client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH
)
# ---------------------------------------------------
# Extrai dados estruturados da mensagem do Telegram.
# Retorna dict ou None se não casar com o padrão.
# ---------------------------------------------------
def parse_signal_message(text: str):
    # Normaliza texto
    text = text.strip().replace("\r", "")

    # Regex principal
    pattern = re.compile(
        r'^(?P<exchange>\w+):(?P<symbol>\w+)\s+deu\s+'
        r'(?P<signal>.+?)\s+nos?\s+'
        r'(?P<time>\d+)\s+minutos?.*?\n+'
        r'Preço:\s*(?P<price>[\d\.]+)',
        re.IGNORECASE | re.DOTALL
    )

    match = pattern.search(text)
    if not match:
        return None

    exchange = match.group("exchange").upper()
    symbol = match.group("symbol").upper()
    signal = match.group("signal").strip().lower()
    timeframe = f'{match.group("time")} minutos'
    price = match.group("price").replace(".", ",")

    return {
        "exchange": exchange,
        "symbol": symbol,
        "signal": signal,
        "timeframe": timeframe,
        "price": price
    }

# -------------------------------------------------------------------------
# Função que retorna a data operacional considerando início às 21h (SP).
# -------------------------------------------------------------------------

def get_operational_date(now):

    if now.hour < 21:
        return (now.date() - timedelta(days=1))
    return now.date()

# -------------------------------------------------
# Função para gravar o log tabulado
# -------------------------------------------------
def write_log(data: dict):
    os.makedirs(LOG_DIR, exist_ok=True)

    tz_brasilia = timezone(timedelta(hours=-3))
    now = datetime.now(tz_brasilia)

    operational_date = get_operational_date(now)
    file_name = f"log_{operational_date.isoformat()}.txt"
    log_path = os.path.join(LOG_DIR, file_name)

    header = "Data\tHora\tExchange\tMoeda\tSinal\tGrafico\tPreco\n"
    file_exists = os.path.exists(log_path)

    data_str = now.strftime("%d/%m/%Y")
    hora_str = now.strftime("%H:%M:%S")

    with open(log_path, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write(header)

        f.write(
            f"{data_str}\t"
            f"{hora_str}\t"
            f"{data['exchange']}\t"
            f"{data['symbol']}\t"
            f"{data['signal']}\t"
            f"{data['timeframe']}\t"
            f"{data['price']}\n"
        )

# -------------------------------------------------
# Listener de mensagens
# -------------------------------------------------
@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def forward_message(event):
    try:
        text = event.message.text or ""

        # -------- LOG --------
        parsed = parse_signal_message(text)
        if parsed:
            write_log(parsed)
            print(f"[LOG] Registrado: {parsed}")

        # -------- FORWARD --------
        if event.message.media:
            await client.send_file(
                TARGET_CHAT_ID,
                event.message.media,
                caption=text
            )
        else:
            await client.send_message(
                TARGET_CHAT_ID,
                text
            )

        print("Mensagem encaminhada")

    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

# -------------------------------------------------
# Função para enviar o log para o Telegram
# -------------------------------------------------
async def send_daily_log():
    tz_brasilia = timezone(timedelta(hours=-3))
    now = datetime.now(tz_brasilia)

    operational_date = get_operational_date(now)
    file_name = f"log_{operational_date.isoformat()}.txt"
    log_path = os.path.join(LOG_DIR, file_name)

    if not os.path.exists(log_path):
        print("[LOG] Nenhum arquivo para enviar")
        return

    caption = (
        f"📊 Log diário\n"
        f"Data operacional: {operational_date.strftime('%d/%m/%Y')}\n"
        f"Horário envio: {now.strftime('%H:%M')}"
    )

    await client.send_file(
        TARGET_CHAT_ID,
        log_path,
        caption=caption
    )

    print("[LOG] Arquivo enviado ao Telegram")

# -------------------------------------------------
# Scheduler assíncrono (09h e 21h)
# -------------------------------------------------
async def scheduler():
    tz_brasilia = timezone(timedelta(hours=-3))

    while True:
        now = datetime.now(tz_brasilia)
        current_time = now.strftime("%H:%M")

        if current_time in ("09:00", "21:00"):
            print(f"[SCHEDULER] Envio programado {current_time}")
            await send_daily_log()
            await asyncio.sleep(60)  # evita envio duplicado no mesmo minuto

        await asyncio.sleep(20)

# -------------------------------------------------
# Execução principal (versão final)
# -------------------------------------------------
async def main():
    if MODE == "LOGIN":
        print("Modo LOGIN: gerando sessão...")
        await client.start()
        print("Sessão válida criada com sucesso.")
        return

    print("Modo BOT: iniciado...")
    await client.start()
    asyncio.create_task(scheduler())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
