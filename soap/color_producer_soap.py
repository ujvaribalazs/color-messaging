import random
import time
import logging
import os
from zeep import Client

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("color_producer")

# SOAP szolgáltatás elérhetősége környezeti változókkal
SOAP_HOST = os.environ.get('SOAP_SERVICE_HOST', 'localhost')
SOAP_PORT = os.environ.get('SOAP_SERVICE_PORT', '8000')
SOAP_WSDL_URL = f'http://{SOAP_HOST}:{SOAP_PORT}/?wsdl'



def generate_random_color():
    """
    Véletlenszerűen választ egy színt a RED, GREEN és BLUE közül.

    :return: A véletlenszerűen választott szín
    """
    colors = ["RED", "GREEN", "BLUE"]
    return random.choice(colors)


def run_color_producer():
    """
    Színeket küld a SOAP webszolgáltatásnak time.sleep( ... ) időnként.
    """
    logger.info(f"Connecting to SOAP service at {SOAP_WSDL_URL}")
    client = Client(SOAP_WSDL_URL) # létrejön a proxy

    logger.info("Color Producer started. Sending random colors to SOAP service...")

    while True:
        try:
            # Véletlenszerű szín generálása
            color = generate_random_color()

            # Szín küldése a SOAP szolgáltatásnak
            response = client.service.send_color_to_queue(color)

            logger.info(f"Sent color: {color}, Response: {response}")

            # Várunk valamennyi másodpercet a következő küldésig
            time.sleep(.5)

        except Exception as e:
            logger.error(f"Error sending color: {e}")
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    # Várunk néhány másodpercet, hogy a SOAP szolgáltatás elinduljon
    logger.info("Waiting for SOAP service to start...")
    time.sleep(5)
    run_color_producer()