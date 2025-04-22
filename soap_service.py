import logging
from wsgiref.simple_server import make_server

import pika
from spyne import Application, ServiceBase, rpc, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("soap_service")

# RabbitMQ kapcsolati adatok
RABBITMQ_HOST = 'localhost'  # Docker környezetben ez 'rabbitmq' lesz
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'
COLOR_QUEUE = '/queue/colorQueue'


# noinspection PyMethodParameters
class ColorService(ServiceBase):
    """
    SOAP webszolgáltatás, amely színeket fogad és továbbítja azokat az üzenetsorba.
    """

    @rpc(Unicode, _returns=Unicode)
    def send_color(ctx, color):
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

            return f"Color {color} successfully sent to the message queue"
        except Exception as e:
            logger.error(f"Error sending color to queue: {e}")
            return f"Error sending color to queue: {e}"


def run_soap_server():
    """
    Elindítja a SOAP webszolgáltatást.
    """
    # SOAP alkalmazás konfigurálása
    application = Application([ColorService],
                              tns='http://color.service.example',
                              in_protocol=Soap11(validator='lxml'),
                              out_protocol=Soap11())

    # WSGI alkalmazás létrehozása
    wsgi_application = WsgiApplication(application)

    # WSGI szerver elindítása
    server = make_server('0.0.0.0', 8000, wsgi_application)
    logger.info("SOAP Service started at http://localhost:8000")
    logger.info("WSDL available at http://localhost:8000/?wsdl")

    server.serve_forever()


if __name__ == "__main__":
    run_soap_server()
