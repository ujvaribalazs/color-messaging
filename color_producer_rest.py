import random
import time
import logging
import requests
import json

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("color_producer")

# REST API szolgáltatás elérhetősége
REST_API_URL = 'http://localhost:5000/api/colors'  # Docker környezetben ez 'http://rest_service:5000/api/colors' lesz


def generate_random_color():
    """
    Véletlenszerűen választ egy színt a RED, GREEN és BLUE közül.
    :return: A véletlenszerűen választott szín
    """
    colors = ["RED", "GREEN", "BLUE"]
    return random.choice(colors)


def run_color_producer():
    """
    Színeket küld a REST API-nak másodpercenként.
    """
    logger.info("Color Producer started. Sending random colors to REST API service...")

    while True:
        try:
            # Véletlenszerű szín generálása
            color = generate_random_color()

            # Szín küldése a REST API-nak
            payload = {"color": color}
            headers = {"Content-Type": "application/json"}

            response = requests.post(
                REST_API_URL,
                data=json.dumps(payload),
                headers=headers
            )

            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Sent color: {color}, Response: {response_data.get('message', 'No message')}")
            else:
                logger.error(f"Error response: {response.status_code} - {response.text}")

            # Várunk 1 másodpercet a következő küldésig
            time.sleep(.1)

        except Exception as e:
            logger.error(f"Error sending color: {e}")
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    # Várunk néhány másodpercet, hogy a REST API szolgáltatás elinduljon
    logger.info("Waiting for REST API service to start...")
    time.sleep(5)
    run_color_producer()
