from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 21870185
API_HASH = "7549ae5c39ca8476d330d2e74776d9dd"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("SESSION_STRING:")
    print(client.session.save())
