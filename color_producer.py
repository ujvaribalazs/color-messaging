import random
import time
import logging
from zeep import Client

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("color_producer")

# SOAP szolgáltatás elérhetősége
SOAP_WSDL_URL = 'http://localhost:8000/?wsdl'  # Docker környezetben ez 'http://soap_service:8000/?wsdl' lesz


def generate_random_color():
    """
    Véletlenszerűen választ egy színt a RED, GREEN és BLUE közül.

    :return: A véletlenszerűen választott szín
    """
    colors = ["RED", "GREEN", "BLUE"]
    return random.choice(colors)


def run_color_producer():
    """
    Színeket küld a SOAP webszolgáltatásnak másodpercenként.
    """
    client = Client(SOAP_WSDL_URL)

    logger.info("Color Producer started. Sending random colors to SOAP service...")

    while True:
        try:
            # Véletlenszerű szín generálása
            color = generate_random_color()

            # Szín küldése a SOAP szolgáltatásnak
            response = client.service.send_color(color)

            logger.info(f"Sent color: {color}, Response: {response}")

            # Várunk 1 másodpercet a következő küldésig
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error sending color: {e}")
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    # Várunk néhány másodpercet, hogy a SOAP szolgáltatás elinduljon
    logger.info("Waiting for SOAP service to start...")
    time.sleep(5)
    run_color_producer()
