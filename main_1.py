#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# -------------------------------------------------
# Ambiente local → carrega .env (se existir)
# Ambiente web  → usa apenas env vars
# -------------------------------------------------
try:
    from dotenv import load_dotenv
    if os.path.exists(".env"):
        load_dotenv()
        print("[ENV] .env carregado (local)")
    else:
        print("[ENV] execução web (sem .env)")
except ImportError:
    print("[ENV] python-dotenv ausente (execução web)")

# -------------------------------------------------
# Variáveis obrigatórias
# -------------------------------------------------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SOURCE_CHAT_ID = int(os.environ["SOURCE_CHAT_ID"])
TARGET_CHAT_ID = int(os.environ["TARGET_CHAT_ID"])

# Opcional: controla modo de execução
MODE = os.getenv("MODE", "BOT")

# Sessão via StringSession (usuário comum)
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")

if not SESSION_STRING:
    raise RuntimeError("TELEGRAM_SESSION_STRING não definida")

# -------------------------------------------------
# Cliente Telegram (válido local e Railway)
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
# Execução principal
# -------------------------------------------------
async def main():
    if MODE == "LOGIN":
        print("Modo LOGIN: apenas valida sessão")
        await client.start()
        print("Sessão válida")
        return

    print("Modo BOT: iniciado")
    await client.start()
    await client.run_until_disconnected()

# -------------------------------------------------
# Entry point
# -------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
