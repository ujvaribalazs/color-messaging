import os
import pika
import logging
import threading
import time

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("color_processor")
logging.getLogger("pika").setLevel(logging.WARNING)

# RabbitMQ kapcsolati adatok
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASS', 'guest')
COLOR_QUEUE = 'colorQueue'
STATISTICS_QUEUE = 'colorStatistics'
DLX_NAME = 'dlx'  # Dead-letter exchange neve
DLQ_NAME = COLOR_QUEUE + '.dlq'  # Dead-letter queue neve


class ColorMessageProcessor:
    def __init__(self, color):
        self.message_count = 0
        self.color = color
        self.queue_name = COLOR_QUEUE

        # Kapcsolódás a RabbitMQ-hoz
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            )
        )
        self.channel = self.connection.channel()

        # Dead-letter exchange létrehozása
        self.channel.exchange_declare(exchange=DLX_NAME, exchange_type='fanout')

        # Fő üzenetsor létrehozása dead-letter exchange-csel
        self.channel.queue_declare(
            queue=self.queue_name,
            arguments={
                'x-dead-letter-exchange': DLX_NAME
            }
        )

        # Dead-letter queue létrehozása és bindolása a DLX-hez
        self.channel.queue_declare(queue=DLQ_NAME)
        self.channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME)

        # Statisztikai sor létrehozása
        self.channel.queue_declare(queue=STATISTICS_QUEUE)

        # QoS és feliratkozás
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self.process_message,
            auto_ack=False
        )

        logger.info(f"{self.color} Message Processor started. Waiting for messages on {self.queue_name}...")

    def process_message(self, ch, method, properties, body):
        message = body.decode('utf-8')

        if properties.headers and properties.headers.get('COLOR') == self.color:
            logger.info(f"MDB {self.color} processing message: {message}")
            self.message_count += 1

            if self.message_count % 10 == 0:
                self.send_statistics()

            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logger.info(f"MDB {self.color} rejecting message to DLQ: {message}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)  # DLQ-ba megy

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
    threads = []
    for color in ["RED", "GREEN", "BLUE"]:
        thread = threading.Thread(target=processor_thread, args=(color,))
        thread.daemon = True
        threads.append(thread)
        thread.start()
        logger.info(f"Started {color} processor thread")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping all processors...")

    for thread in threads:
        thread.join(timeout=5)

    logger.info("All processors stopped")
