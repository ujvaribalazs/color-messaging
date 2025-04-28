import pika
import logging
import threading
import time

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


class ColorMessageProcessor:
    def __init__(self, color):
        self.message_count = 0
        self.color = color

        # Kapcsolódás a RabbitMQ-hoz
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            )
        )
        self.channel = self.connection.channel()

        # Üzenetsorok létrehozása
        self.channel.queue_declare(queue=COLOR_QUEUE)
        self.channel.queue_declare(queue=STATISTICS_QUEUE)

        # QoS és feliratkozás
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=COLOR_QUEUE,
            on_message_callback=self.process_message,
            auto_ack=False
        )

        logger.info(f"{self.color} Message Processor started. Waiting for messages...")

    def process_message(self, ch, method, properties, body):

        """
        Paraméter   | Mit jelent?                                                   | Mi tölti fel?
        ch          | a channel objektum, amin az üzenet érkezett                   | RabbitMQ tölti
        method      | üzenet metaadatai, pl. delivery_tag (az üzenet azonosítója)   | RabbitMQ tölti
        properties  | üzenet tulajdonságai (pl. fejlécek, user-defined dolgok)      | RabbitMQ tölti
        body        | maga az üzenet tartalma | RabbitMQ tölti
        """

        message = body.decode('utf-8')
        logger.info(f"MDB {self.color} received message: {message}")

        # Csak a megfelelő színű üzeneteket dolgozzuk fel
        if message == self.color:
            logger.info(f"Processing {self.color} message")
            self.message_count += 1


            # Ha elértük a 10 üzenetet, statisztikát küldünk
            if self.message_count % 10 == 0:
                self.send_statistics()
        else:
            logger.info(f"Ignoring {message} message (not {self.color}), requeuing...")
            # Nem az én üzenetem, visszarakjuk
        # Nyugtázzuk az üzenet feldolgozását
        ch.basic_ack(delivery_tag=method.delivery_tag)


    def send_statistics(self):
        statistic_message = f"10 '{self.color}' messages has been processed"

        self.channel.basic_publish(
            exchange='',
            routing_key=STATISTICS_QUEUE,
            body=statistic_message.encode('utf-8')
        )

        logger.info(f"Sent statistics: {statistic_message}")

    def start(self):
        self.channel.start_consuming()

    def stop(self):
        if self.connection.is_open:
            self.channel.stop_consuming()
            self.connection.close()
            logger.info(f"{self.color} processor connection closed")


def processor_thread(color):
    processor = ColorMessageProcessor(color)
    try:
        processor.start()
    except Exception as e:
        logger.error(f"Error in {color} processor: {e}")
    finally:
        processor.stop()


if __name__ == "__main__":
    # Létrehozzuk a három szálat a három színnek
    threads = []
    for color in ["RED", "GREEN", "BLUE"]:
        thread = threading.Thread(target=processor_thread, args=(color,))
        thread.daemon = True  # Főprogram leállása esetén a szálak is leállnak
        threads.append(thread)
        thread.start()
        logger.info(f"Started {color} processor thread")

    # Várunk amíg a főprogram fut
    try:
        # A főszál addig fut, amíg a felhasználó meg nem szakítja
        while True:

            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping all processors...")

    # Megvárjuk, hogy minden szál befejeződjön
    for thread in threads:
        thread.join(timeout=5)

    logger.info("All processors stopped")