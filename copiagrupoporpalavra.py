# NAO ESTÁ FUNCIONANDO



#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from telethon import TelegramClient, events
from dotenv import load_dotenv

# -------------------------------------------------
# Carregar variáveis
# -------------------------------------------------
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))

# -------------------------------------------------
# Palavras-chave para filtro
# -------------------------------------------------
KEYWORDS = [
    "SANTA",
#    "btc",
#    "rompimento"
]

# -------------------------------------------------
# Cliente Telegram
# -------------------------------------------------
client = TelegramClient("session_forwarder", API_ID, API_HASH)

# -------------------------------------------------
# Listener
# -------------------------------------------------
@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def filter_and_forward(event):
    try:
        text = ""

        # Texto normal
        if event.message.text:
            text = event.message.text

        # Legenda de mídia
        elif event.message.caption:
            text = event.message.caption

        if not text:
            return

        text_lower = text.lower()

        # Verifica se contém alguma palavra-chave
        if any(keyword in text_lower for keyword in KEYWORDS):
            await event.message.forward_to(TARGET_CHAT_ID)
            print("Mensagem copiada (match encontrado)")

    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

# -------------------------------------------------
# Execução
# -------------------------------------------------
def main():
    print("Filtro de mensagens ativo...")
    client.start()
    client.run_until_disconnected()

if __name__ == "__main__":
    main()
