# VERSAO 1 - FUNCIONA LOCAL e WEB


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

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
# SESSION_NAME = os.environ.get("SESSION_NAME", "session_forwarder") = usado na versão local

SESSION_NAME = "/app/session_forwarder"

# -------------------------------------------------
# Cliente Telegram
# -------------------------------------------------
# client = TelegramClient(SESSION_NAME, API_ID, API_HASH).start(bot_token=BOT_TOKEN) = usado na versão local
#client = TelegramClient(
#    SESSION_NAME,
#    API_ID,
#    API_HASH
#)


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
@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def forward_message(event):
    try:
        if event.message.media:
            await client.send_file(
                TARGET_CHAT_ID,
                event.message.media,
                caption=event.message.text
            )
        else:
            await client.send_message(
                TARGET_CHAT_ID,
                event.message.text or ""
            )

        print("Mensagem encaminhada")

    except Exception as e:
        print(f"Erro ao encaminhar mensagem: {e}")

# -------------------------------------------------
# Execução principal (versão local)
# -------------------------------------------------
# async def main():
#    print("Bot iniciado Railway BOT")
#    await client.start()
#    await client.run_until_disconnected()

# -------------------------------------------------
# Execução principal (versão web)
# -------------------------------------------------
async def main():
    if MODE == "LOGIN":
        print("Modo LOGIN: gerando sessão...")
        await client.start()
        print("Sessão válida criada com sucesso.")
        return

    print("Modo BOT: iniciado...")
    await client.start()
    await client.run_until_disconnected()
#import asyncio

# -----------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
