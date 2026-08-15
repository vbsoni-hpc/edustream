import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

if not API_ID or not API_HASH:
    print("Error: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
    exit(1)

async def main():
    print("Generating new Telegram String Session...")
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()
    
    session_string = client.session.save()
    print("\n" + "="*60)
    print("SUCCESS! Here is your new TELEGRAM_STRING_SESSION:")
    print("="*60)
    print(session_string)
    print("="*60)
    print("\nCopy the text above and update your .env file with it:")
    print("TELEGRAM_STRING_SESSION=\"...\"\n")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
