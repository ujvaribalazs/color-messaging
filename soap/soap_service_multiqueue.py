import os
import logging
from wsgiref.simple_server import make_server  #WSGI szerver
# a SOAP szolgáltatásokat mindig valamilyen HTTP szerveren keresztül kell elérhetővé tenni,
# mivel XML üzeneteiket HTTP protokollon keresztül továbbítják.

import pika # RabbitMQ kliens

from spyne import Application, ServiceBase, rpc, Unicode
""" SOAP webszolgáltatások létrehozására szolgáló Python könyvtár
    Application: A Spyne alkalmazás alaposztálya, amely összefogja a szolgáltatásokat, protokollokat és a szervert
    ServiceBase: Alap osztály a webszolgáltatás definíciókhoz - a ColorService ebből származik
    rpc: Dekorátor, amely megjelöli a függvényeket, hogy azok távoli eljáráshívást (Remote Procedure Call) valósítanak meg
    Unicode: Adattípus definíció, amely meghatározza, hogy a paraméterek és visszatérési értékek szöveges adatok"""

from spyne.protocol.soap import Soap11

"""A SOAP 1.1 protokoll implementációját importálja
   Ez határozza meg, hogyan kell kódolni/dekódolni a SOAP XML kéréseket és válaszokat"""

from spyne.server.wsgi import WsgiApplication # WSGI kompatibilis alkalmazás-wrapper

""" Ez teszi lehetővé, hogy a SOAP szolgáltatás bármely WSGI-kompatibilis webszerverrel működhessen (mint pl. a wsgiref)
    Hidat képez a SOAP alkalmazás és a HTTP webszerver között """

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("soap_service")
logging.getLogger("pika").setLevel(logging.WARNING)

"""Együtt ezek az importok lehetővé teszik, hogy:

     Definiálunk egy szolgáltatást (ColorService)
     Hozzáadjunk távoli eljáráshívásokat (@rpc dekorátorral)
     Beállítsuk a SOAP protokollt
     Összekapcsoljuk a szolgáltatást egy WSGI-kompatibilis webszerverrel
"""


# RabbitMQ kapcsolati adatok környezeti változókból
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASS', 'guest')

def setup_queues():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        )
    )
    channel = connection.channel()
    channel.exchange_declare(exchange='color_exchange', exchange_type='direct')

    colors = ['red', 'green', 'blue']
    for color in colors:
        queue_name = f'queue_{color}'
        routing_key = f'color.{color}'
        channel.queue_declare(queue=queue_name)
        channel.queue_bind(exchange='color_exchange', queue=queue_name, routing_key=routing_key)

    connection.close()

# noinspection PyMethodParameters
class ColorService(ServiceBase):
    """
    SOAP webszolgáltatás, amely színeket fogad és továbbítja azokat az üzenetsorba.
    """

    @rpc(Unicode, _returns=Unicode)
    def send_color_to_queue(ctx, color):
        """
        Színeket fogad SOAP üzeneteken keresztül és továbbítja őket az üzenetsorba.

        :param color: A szín neve (RED, GREEN vagy BLUE)
        :return: Visszaigazolás az üzenet fogadásáról
        """
        logger.info(f"Received color: {color}")

        # Ellenőrizzük, hogy a szín megfelelő-e
        if color not in ["RED", "GREEN", "BLUE"]:
            return f"Invalid color: {color}. Only RED, GREEN, or BLUE are supported."

        try:
            # Kapcsolódás a RabbitMQ-hoz
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
                )
            )
            channel = connection.channel()

            # Exchange létrehozása (ha még nincs)
            channel.exchange_declare(exchange='color_exchange', exchange_type='direct')

            # Üzenet küldése az exchange-be szín szerint
            routing_key = f"color.{color.lower()}"  # pl. color.red
            channel.basic_publish(
                exchange='color_exchange',
                routing_key=routing_key,
                body=color.upper()
            )

            connection.close()
            """
            A RabbitMQ-val történő kommunikáció során a "csatorna" (channel) egy logikai kapcsolatot jelent 
            a fizikai kapcsolaton belül. Azért kell csatornát létrehozni, mert:

            Erőforrás-hatékonyság: Egy fizikai TCP kapcsolaton belül több logikai csatornát lehet létrehozni, 
            ami sokkal erőforrás-hatékonyabb, mintha minden művelethez külön TCP kapcsolatot nyitnánk.
            Párhuzamos kommunikáció: A csatornák lehetővé teszik, hogy egyidejűleg több kommunikációs folyamatot 
            bonyolítsunk le ugyanazon a kapcsolaton.
            Művelet-szeparáció: Különböző üzenetsorokkal vagy exchange-ekkel való kommunikációt különböző csatornákon 
            keresztül kezelhetünk, ami elkülöníti a logikát.

            A csatornát a connection.channel() hívással hozzuk létre, és minden RabbitMQ művelet 
            (pl. üzenetsor létrehozása, üzenet küldése) ezen a csatornán keresztül történik.
            """





            return f"Color {color} successfully sent to the message queue"
        except Exception as e:
            logger.error(f"Error sending color to queue: {e}")
            return f"Error sending color to queue: {e}"
            # ezek a stringek válaszként mennek vissza a SOAP kliensnek.

def run_soap_server():
    """
    Elindítja a SOAP webszolgáltatást.
    """
    # SOAP alkalmazás konfigurálása
    application = Application([ColorService],
                              tns='http://color.service.example',
                              in_protocol=Soap11(validator='lxml'),
                              out_protocol=Soap11())

    """ WSGI alkalmazás létrehozása
        A WsgiApplication becsomagolja a SOAP alkalmazást egy WSGI-kompatibilis alkalmazásba, amely lehetővé teszi, 
        hogy bármely WSGI-kompatibilis webszerver futtatni tudja.
    """

    wsgi_application = WsgiApplication(application)

    # WSGI szerver elindítása
    server = make_server('0.0.0.0', 8000, wsgi_application)
    logger.info(f"SOAP Service started at http://0.0.0.0:8000")
    logger.info(f"WSDL available at http://0.0.0.0:8000/?wsdl")

    server.serve_forever()


if __name__ == "__main__":
    setup_queues()
    run_soap_server()
