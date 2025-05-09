import os
import logging
from wsgiref.simple_server import make_server  # WSGI szerver

import pika  # RabbitMQ kliens

from spyne import Application, ServiceBase, rpc, Unicode
"""
SOAP webszolgáltatások létrehozására szolgáló Python könyvtár.
- Application: A Spyne alkalmazás alaposztálya, amely összefogja a szolgáltatásokat, protokollokat és a szervert.
- ServiceBase: Alaposztály a webszolgáltatás definíciókhoz — a ColorService ebből származik.
- rpc: Dekorátor, amely megjelöli a függvényeket, hogy azok távoli eljáráshívást (Remote Procedure Call) valósítanak meg.
- Unicode: Adattípus definíció, amely meghatározza, hogy a paraméterek és visszatérési értékek szöveges adatok.
"""

from spyne.protocol.soap import Soap11
"""
A SOAP 1.1 protokoll implementációját importálja.
Ez határozza meg, hogyan kell kódolni/dekódolni a SOAP XML kéréseket és válaszokat.
"""

from spyne.server.wsgi import WsgiApplication  # WSGI kompatibilis alkalmazás-wrapper
"""
Ez teszi lehetővé, hogy a SOAP szolgáltatás bármely WSGI-kompatibilis webszerverrel működhessen (mint pl. a wsgiref).
Hidat képez a SOAP alkalmazás és a HTTP webszerver között.
"""

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("soap_service")
logging.getLogger("pika").setLevel(logging.WARNING)

"""
Ezek az importok és beállítások lehetővé teszik, hogy:
- Definiáljunk egy szolgáltatást (ColorService),
- Hozzáadjunk távoli eljáráshívásokat (@rpc dekorátorral),
- Beállítsuk a SOAP protokollt,
- Összekapcsoljuk a szolgáltatást egy WSGI-kompatibilis webszerverrel.
"""

# RabbitMQ kapcsolati adatok környezeti változókból
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASS', 'guest')
COLOR_QUEUE = 'colorQueue'
STATISTICS_QUEUE = 'colorStatistics'
DLX_NAME = 'dlx'  # Dead-letter exchange neve
DLQ_NAME = COLOR_QUEUE + '.dlq'  # Dead-letter queue neve

# Globális RabbitMQ kapcsolat és csatorna
connection = None
channel = None


def setup_rabbitmq():
    """
    RabbitMQ kapcsolat és csatorna egyszeri inicializálása.
    Itt hozzuk létre az exchange-eket és a queue-kat.
    """
    global connection, channel
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        )
    )
    channel = connection.channel()

    # Dead-letter exchange létrehozása (ha még nem létezik)
    channel.exchange_declare(exchange=DLX_NAME, exchange_type='fanout')

    # Dead-letter queue létrehozása
    channel.queue_declare(queue=DLQ_NAME)

    # Dead-letter queue kötése a dead-letter exchange-hez
    channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME)

    # Fő üzenetsor létrehozása dead-letter exchange-szel
    channel.queue_declare(
        queue=COLOR_QUEUE,
        arguments={'x-dead-letter-exchange': DLX_NAME}
    )


class ColorService(ServiceBase):
    """
    SOAP webszolgáltatás, amely színeket fogad és továbbítja azokat az üzenetsorba.
    """

    @rpc(Unicode, _returns=Unicode)
    def send_color_to_queue(ctx, color):
        """
        Színeket fogad SOAP üzeneteken keresztül és továbbítja őket az üzenetsorba.

        :param color: A szín neve (RED, GREEN vagy BLUE).
        :return: Visszaigazolás az üzenet fogadásáról.
        """
        logger.info(f"Received color: {color}")

        # Ellenőrizzük, hogy a szín megfelelő-e
        if color not in ["RED", "GREEN", "BLUE"]:
            return f"Invalid color: {color}. Only RED, GREEN, or BLUE are supported."

        try:
            # A globális channel használata újranyitás helyett
            channel.basic_publish(
                exchange='',  # Default exchange
                routing_key=COLOR_QUEUE,  # A sor neve
                body=color,
                properties=pika.BasicProperties(
                    headers={'COLOR': color}
                )
            )
            return f"Color {color} successfully sent to the message queue"
        except Exception as e:
            logger.error(f"Error sending color to queue: {e}")
            return f"Error sending color to queue: {e}"
            # Ezek a stringek válaszként mennek vissza a SOAP kliensnek.


def run_soap_server():
    """
    Elindítja a SOAP webszolgáltatást.
    """
    # RabbitMQ setup egyszer, induláskor
    setup_rabbitmq()

    # SOAP alkalmazás konfigurálása
    application = Application(
        [ColorService],
        tns='http://color.service.example',
        in_protocol=Soap11(validator='lxml'),
        out_protocol=Soap11()
    )

    # WSGI alkalmazás létrehozása
    wsgi_application = WsgiApplication(application)

    # WSGI szerver elindítása
    server = make_server('0.0.0.0', 8000, wsgi_application)
    logger.info("SOAP Service started at http://localhost:8000")
    logger.info("WSDL available at http://localhost:8000/?wsdl")

    server.serve_forever()


if __name__ == "__main__":
    run_soap_server()
