# VERSAO 1 - FUNCIONA LOCAL e WEB

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import re
from datetime import datetime, timezone, timedelta


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


# -------------------------------------------------
# Listener de mensagens
# -------------------------------------------------
#@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
#async def forward_message(event):
#    try:
#        if event.message.media:
#            await client.send_file(
#                TARGET_CHAT_ID,
#                event.message.media,
#                caption=event.message.text
#            )
#        else:
#            await client.send_message(
#                TARGET_CHAT_ID,
#                event.message.text or ""
#            )
#
#        print("Mensagem encaminhada")
#
#    except Exception as e:
#        print(f"Erro ao encaminhar mensagem: {e}")


#---------------------------------------------------------
# Esta função interpreta os padrões de mensagem
# --------------------------------------------------------

def parse_signal_message(text: str):
    """
    Extrai dados estruturados da mensagem do Telegram.
    Retorna dict ou None se não casar com o padrão.
    """

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
#---------------------------------------------------------
# Esta função grava log
# --------------------------------------------------------
def get_daily_log_filename(date=None):
    tz = timezone(timedelta(hours=-3))
    if date is None:
        date = datetime.now(tz)

    day_str = date.strftime("%Y-%m-%d")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, f"telegram_signals_{day_str}.tsv")

def write_log(data: dict):
    tz = timezone(timedelta(hours=-3))
    now = datetime.now(tz)

    log_file = get_daily_log_filename()

    header = "Data\tHora\tExchange\tMoeda\tSinal\tGrafico\tPreco\n"
    file_exists = os.path.exists(log_file)

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write(header)

            line = (
                f"{now.strftime('%Y-%m-%d')}\t"
                f"{now.strftime('%H:%M:%S')}\t"
                f"{data['exchange']}\t"
                f"{data['symbol']}\t"
                f"{data['signal']}\t"
                f"{data['timeframe']}\t"
                f"{data['price']}\n"
            )
            f.write(line)

    except Exception as e:
        print(f"[ERRO LOG] Falha ao gravar arquivo {log_file}: {e}")

async def send_daily_log():
    tz = timezone(timedelta(hours=-3))
    today = datetime.now(tz)

    log_file = get_daily_log_filename(today)

    if not os.path.exists(log_file):
        await client.send_message(
            TARGET_CHAT_ID,
            f"📄 Log diário {today.strftime('%Y-%m-%d')}:\nNenhum sinal registrado."
        )
        return

    try:
        await client.send_file(
            TARGET_CHAT_ID,
            log_file,
            caption=f"📄 Log diário {today.strftime('%Y-%m-%d')}"
        )

        os.remove(log_file)
        print(f"[LOG] Arquivo enviado e removido: {log_file}")

    except Exception as e:
        print(f"[ERRO] Falha ao enviar log diário: {e}")

async def daily_log_scheduler():
    tz = timezone(timedelta(hours=-3))

    while True:
        now = datetime.now(tz)

        send_time = now.replace(hour=21, minute=00, second=0, microsecond=0)

        if now >= send_time:
            send_time += timedelta(days=1)

        sleep_seconds = (send_time - now).total_seconds()

        print(
            f"[SCHEDULER] Próximo envio do log em "
            f"{int(sleep_seconds // 3600)}h "
            f"{int((sleep_seconds % 3600) // 60)}m"
        )

        await asyncio.sleep(sleep_seconds)

        await send_daily_log()

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
    asyncio.create_task(daily_log_scheduler()) # ▶ inicia scheduler diário
    await client.run_until_disconnected()

#---------------------------------------------------------
# Nova função 
# --------------------------------------------------------

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



if __name__ == "__main__":
    asyncio.run(main())
