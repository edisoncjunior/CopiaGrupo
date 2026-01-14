# VERSAO APENAS LOCAL

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from telethon import TelegramClient, events
from dotenv import load_dotenv

# -------------------------------------------------
# Carrega variáveis de ambiente
# -------------------------------------------------
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))

# -------------------------------------------------
# Inicializa cliente
# -------------------------------------------------
client = TelegramClient("session_forwarder", API_ID, API_HASH)

# -------------------------------------------------
# Listener em tempo real
# -------------------------------------------------
@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def forward_message(event):
    try:
        if event.message.text:
            await client.send_message(
                TARGET_CHAT_ID,
                event.message.text
            )

        elif event.message.media:
            await client.send_file(
                TARGET_CHAT_ID,
                event.message.media,
                caption=event.message.text
            )

        print("Mensagem encaminhada com sucesso")

    except Exception as e:
        print(f"Erro ao encaminhar mensagem: {e}")

# -------------------------------------------------
# Execução principal
# -------------------------------------------------
def main():
    print("Bot de encaminhamento iniciado...")
    client.start()
    client.run_until_disconnected()

if __name__ == "__main__":
    main()
