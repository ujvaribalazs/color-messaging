import pika
import logging

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("statistics_client")

# RabbitMQ kapcsolati adatok
RABBITMQ_HOST = 'localhost'  # Docker környezetben ez 'rabbitmq' lesz
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'
STATISTICS_QUEUE = '/queue/colorStatistics'


# noinspection PyMethodMayBeStatic
class StatisticsClient:
    """
    Kliens, amely a statisztika üzenetsorból olvassa az üzeneteket.
    """

    def __init__(self):
        """
        Inicializálja a klienst és beállítja a kapcsolatot.
        """
        # Kapcsolódás a RabbitMQ-hoz
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            )
        )
        self.channel = self.connection.channel()

        # Üzenetsor létrehozása, ha még nem létezik
        self.channel.queue_declare(queue=STATISTICS_QUEUE)

        # Feliratkozás az üzenetsorra
        self.channel.basic_consume(
            queue=STATISTICS_QUEUE,
            on_message_callback=self.process_statistics,
            auto_ack=True
        )

        logger.info("Statistics Client started. Waiting for statistics...")

    def process_statistics(self, ch, method, properties, body):
        """
        Feldolgozza a statisztikai üzeneteket.
        Megjegyzés: Bár ez a metódus nem használja a self paramétert,
        a RabbitMQ callback-mechanizmusa miatt nem lehet statikus metódussá alakítani.

        :param body: Az üzenet tartalma
        """
        message = body.decode('utf-8')
        logger.info(f"Statistics: {message}")
        print(f"Statistics: {message}")  # Explicit kiírás a konzolra

    def start(self):
        """
        Elindítja a statisztikák olvasását.
        """
        self.channel.start_consuming()


if __name__ == "__main__":
    client = StatisticsClient()
    try:
        client.start()
    except KeyboardInterrupt:
        logger.info("Stopping client...")
    finally:
        if client.connection.is_open:
            client.connection.close()
            logger.info("Connection closed")
