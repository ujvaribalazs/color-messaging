import pika
import logging

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mdb_red")

# RabbitMQ kapcsolati adatok
RABBITMQ_HOST = 'localhost'  # Docker környezetben ez 'rabbitmq' lesz
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'
COLOR_QUEUE = 'colorQueue'
STATISTICS_QUEUE = 'colorStatistics'


class RedMessageProcessor:
    """
    A piros üzeneteket feldolgozó komponens.
    """

    def __init__(self):
        """
        Inicializálja a komponenst és a számlálót.
        """
        self.message_count = 0
        self.color = "RED"

        # Kapcsolódás a RabbitMQ-hoz
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            )
        )
        self.channel = self.connection.channel()

        # Üzenetsorok létrehozása, ha még nem léteznek
        self.channel.queue_declare(queue=COLOR_QUEUE)
        self.channel.queue_declare(queue=STATISTICS_QUEUE)

        # Beállítjuk, hogy egyszerre csak egy üzenetet dolgozzon fel, (nem vesz ki újat, amíg az előzőt nem nyugtázta)
        self.channel.basic_qos(prefetch_count=1)

        # Feliratkozás az üzenetsorra a megfelelő szűrővel
        self.channel.basic_consume(
            queue=COLOR_QUEUE,
            on_message_callback=self.process_message, # Ez a callback függvény, amelyet a RabbitMQ hív meg, amikor új üzenet érkezik
            auto_ack=False
        )

        logger.info(f"{self.color} Message Processor started. Waiting for messages...")

    def process_message(self, ch, method, properties, body):
        """
        Feldolgozza a beérkező üzeneteket.

        :param ch: A csatorna
        :param method: Az üzenet metódusa
        :param properties: Az üzenet tulajdonságai
        :param body: Az üzenet tartalma
        """
        message = body.decode('utf-8') # Dekódolja az üzenetet UTF-8 kódolással (a body egy byte tömb)
        logger.info(f"MDB {self.color} received message: {message}")

        # Csak a piros üzeneteket dolgozzuk fel
        if message == self.color:
            logger.info(f"Processing {self.color} message")
            self.message_count += 1

            # Ha elértük a 10 üzenetet, statisztikát küldünk
            if self.message_count % 10 == 0:
                self.send_statistics()
        else:
            logger.info(f"Ignoring {message} message (not {self.color})")

        # Nyugtázzuk az üzenet feldolgozását
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def send_statistics(self):
        """
        Statisztikát küld a statisztikai üzenetsorba.
        """
        statistic_message = f"10 '{self.color}' messages has been processed"

        self.channel.basic_publish(
            exchange='',
            routing_key=STATISTICS_QUEUE,
            body=statistic_message.encode('utf-8')
        )

        logger.info(f"Sent statistics: {statistic_message}")

    def start(self):
        """
        Elindítja az üzenetfeldolgozást.
        """
        self.channel.start_consuming()

        """
        Az alkalmazás fő szálát blokkolja. A kód ezen a ponton "megáll", és egy végtelen ciklusba lép, ahol a RabbitMQ kapcsolatot figyeli új üzenetekre.
        A callback használata: A callback (process_message) valóban aszinkron abban az értelemben, hogy akkor hívódik meg, amikor egy üzenet érkezik, nem pedig előre meghatározott időközönként. Azonban maga a callback mechanizmus egy szinkron, blokkolt környezetben működik.
        Hogyan működik ez? A start_consuming() hívás után a pika könyvtár belső hurkot indít, amely:
        
        Folyamatosan figyeli a RabbitMQ kapcsolatot
        Amikor üzenet érkezik, meghívja a megadott callback függvényt
        A callback végrehajtása után visszatér a figyelő hurokhoz
        Ez a hurok addig fut, amíg meg nem szakítják (pl. KeyboardInterrupt kivétellel)
        """


if __name__ == "__main__":
    processor = RedMessageProcessor()
    try:
        processor.start()
    except KeyboardInterrupt:
        logger.info("Stopping processor...")
    finally:
        if processor.connection.is_open:
            processor.connection.close()
            logger.info("Connection closed")
