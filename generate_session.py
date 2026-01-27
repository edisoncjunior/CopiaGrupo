from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 30504550
API_HASH = "12a111ab2d8140980971758c9a896474"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("SESSION_STRING:")
    print(client.session.save())
