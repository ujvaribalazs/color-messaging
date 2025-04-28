import asyncio
import aio_pika
import logging



# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("color_processor")

# RabbitMQ kapcsolati adatok
RABBITMQ_HOST = 'localhost'
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'
COLOR_QUEUE = 'colorQueue'
STATISTICS_QUEUE = 'colorStatistics'

class AsyncColorProcessor:
    def __init__(self, color):
        self.color = color
        self.message_count = 0

    async def connect(self):
        self.connection = await aio_pika.connect_robust(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            login=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD
        )
        self.channel = await self.connection.channel()

        # QoS beállítása
        await self.channel.set_qos(prefetch_count=1)

        # Üzenetsorok
        self.color_queue = await self.channel.declare_queue(COLOR_QUEUE)
        self.stats_queue = await self.channel.declare_queue(STATISTICS_QUEUE)

        # Feliratkozás az üzenetekre
        await self.color_queue.consume(self.process_message)

        logger.info(f"{self.color} processor connected and waiting for messages")

    async def process_message(self, message):
        async with message.process():
            body = message.body.decode()
            logger.info(f"MDB {self.color} received message: {body}")

            if body == self.color:
                logger.info(f"Processing {self.color} message")
                self.message_count += 1

                if self.message_count % 10 == 0:
                    await self.send_statistics()
            else:
                logger.info(f"Ignoring {body} message (not {self.color})")

    async def send_statistics(self):
        statistic_message = f"10 '{self.color}' messages has been processed"

        await self.channel.default_exchange.publish(
            aio_pika.Message(body=statistic_message.encode()),
            routing_key=STATISTICS_QUEUE
        )

        logger.info(f"Sent statistics: {statistic_message}")

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info(f"{self.color} processor connection closed")


async def main():
    # Létrehozzuk és elindítjuk mindhárom színfeldolgozót
    processors = []
    for color in ["RED", "GREEN", "BLUE"]:
        processor = AsyncColorProcessor(color)
        await processor.connect()
        processors.append(processor)

    # Futtatjuk, amíg meg nem szakítják
    try:
        # Várakozás végtelen ideig (vagy amíg meg nem szakítják)
        await asyncio.Future()
    finally:
        # Bezárjuk a kapcsolatokat
        for processor in processors:
            await processor.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")