import asyncio
import json
import logging
import random
import time
import websockets

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("websocket_color_producer")

# WebSocket szerver elérhetősége
WEBSOCKET_URL = 'ws://localhost:8765'  # Docker környezetben ez 'ws://websocket_service:8765' lesz


def generate_random_color():
    """
    Véletlenszerűen választ egy színt a RED, GREEN és BLUE közül.
    :return: A véletlenszerűen választott szín
    """
    colors = ["RED", "GREEN", "BLUE"]
    return random.choice(colors)


async def connect_websocket():
    """
    Kapcsolódás a WebSocket szerverhez és színek küldése
    """
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            logger.info("Connected to WebSocket server")

            # Üdvözlő üzenet fogadása
            response = await websocket.recv()
            logger.info(f"Server says: {response}")

            send_count = 0
            start_time = time.time()

            # Fő hurok - színek küldése
            while True:
                try:
                    # Véletlenszerű szín generálása
                    color = generate_random_color()

                    # Szín küldése JSON formátumban
                    await websocket.send(json.dumps({"color": color}))

                    # Válasz fogadása
                    response = await websocket.recv()
                    response_data = json.loads(response)

                    # Számláló növelése és statisztika
                    send_count += 1
                    if send_count % 100 == 0:
                        elapsed = time.time() - start_time
                        rate = send_count / elapsed
                        logger.info(f"Sent {send_count} colors in {elapsed:.2f} seconds ({rate:.2f} colors/sec)")

                    # Napló
                    log_level = logging.INFO if response_data["type"] == "success" else logging.ERROR
                    logger.log(log_level, f"Sent color: {color}, Response: {response_data['message']}")

                    # Várunk, mielőtt a következő színt küldenénk
                    await asyncio.sleep(0.1)  # 0.1 másodpercenként küldünk színt

                except Exception as e:
                    logger.error(f"Error in send loop: {e}")
                    await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        logger.info("Retrying in 5 seconds...")
        await asyncio.sleep(5)
        return await connect_websocket()  # Rekurzív újrapróbálkozás


async def main():
    logger.info("WebSocket Color Producer started")
    logger.info("Waiting for WebSocket service to start...")
    await asyncio.sleep(5)  # Várunk, hogy a szerver elinduljon

    try:
        # Indítjuk a WebSocket kapcsolatot
        await connect_websocket()
    except KeyboardInterrupt:
        logger.info("WebSocket Color Producer stopped by user")


if __name__ == "__main__":
    asyncio.run(main())