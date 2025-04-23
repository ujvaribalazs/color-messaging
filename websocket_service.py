import asyncio
import websockets
import json
import logging
import pika
import concurrent.futures

# Beállítjuk a naplózást
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("new_websocket_service")

# RabbitMQ kapcsolati adatok
RABBITMQ_HOST = 'localhost'  # Docker környezetben ez 'rabbitmq' lesz
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'
COLOR_QUEUE = '/queue/colorQueue'  # Visszaállítottuk az eredeti névformátumot

# Létrehozunk egy thread pool executort a blokkoló műveletek számára
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)


def send_to_rabbitmq(color):
    """
    Üzenet küldése a RabbitMQ-ba (ez egy blokkoló művelet, külön szálban kell futtatni)
    """
    try:
        # Létrehozzuk a RabbitMQ kapcsolati paramétereket
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD),
            connection_attempts=3,
            retry_delay=1
        )

        # Kapcsolódás a RabbitMQ-hoz
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Üzenetsor létrehozása, ha még nem létezik
        channel.queue_declare(queue=COLOR_QUEUE)

        # Üzenet küldése az üzenetsorba
        channel.basic_publish(
            exchange='',
            routing_key=COLOR_QUEUE,
            body=color
        )

        # Kapcsolat lezárása
        connection.close()

        return {"success": True, "message": f"Color {color} successfully sent to the message queue"}

    except Exception as e:
        logger.error(f"Error sending to RabbitMQ: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}


async def handle_websocket(websocket):
    """
    WebSocket kapcsolat kezelése
    """
    try:
        # Üdvözlő üzenet küldése
        await websocket.send(json.dumps({
            "type": "info",
            "message": "Connected to WebSocket Color Service"
        }))

        # Üzenetek fogadása és kezelése
        async for message in websocket:
            try:
                # Üzenet feldolgozása
                data = json.loads(message)

                if 'color' in data:
                    color = data['color']
                    logger.info(f"Received color: {color}")

                    # Ellenőrizzük, hogy a szín megfelelő-e
                    if color not in ["RED", "GREEN", "BLUE"]:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Invalid color: {color}. Only RED, GREEN, or BLUE are supported."
                        }))
                        continue

                    # Küldés a RabbitMQ-ba külön szálban
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(executor, lambda: send_to_rabbitmq(color))

                    if result["success"]:
                        await websocket.send(json.dumps({
                            "type": "success",
                            "message": result["message"]
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": result["message"]
                        }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Missing color parameter"
                    }))

            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                }))

    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Connection closed: {e}")
    except Exception as e:
        logger.error(f"WebSocket handling error: {e}")


async def main():
    # WebSocket szerver indítása
    host = '0.0.0.0'
    port = 8765

    async with websockets.serve(handle_websocket, host, port):
        logger.info(f"WebSocket server is running at ws://{host}:{port}")
        # Várunk addig, amíg leállítják a szervert
        await asyncio.Future()  # Ez egy soha nem teljesülő jövő, hacsak nem szakítják meg


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        executor.shutdown(wait=False)