import logging
from flask import Flask, request, jsonify
import pika

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("rest_service")

# RabbitMQ kapcsolati adatok
RABBITMQ_HOST = 'localhost'  # Docker környezetben ez 'rabbitmq' lesz
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'
COLOR_QUEUE = 'colorQueue'

app = Flask(__name__)


@app.route('/api/colors', methods=['POST'])
def send_color_to_queue():
    """
    Színeket fogad REST API-n keresztül és továbbítja őket az üzenetsorba.
    A kérés formátuma: {"color": "RED"} (vagy GREEN, BLUE)
    """
    content = request.json

    if not content or 'color' not in content:
        return jsonify({"error": "Missing color parameter"}), 400

    color = content['color']
    logger.info(f"Received color: {color}")

    # Ellenőrizzük, hogy a szín megfelelő-e
    if color not in ["RED", "GREEN", "BLUE"]:
        return jsonify({
            "error": f"Invalid color: {color}. Only RED, GREEN, or BLUE are supported."
        }), 400

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

        return jsonify({
            "message": f"Color {color} successfully sent to the message queue"
        }), 200

    except Exception as e:
        logger.error(f"Error sending color to queue: {e}")
        return jsonify({
            "error": f"Error sending color to queue: {str(e)}"
        }), 500


# GET metódus a szolgáltatás elérhetőségének ellenőrzésére
@app.route('/api/colors', methods=['GET'])
def get_colors():
    return jsonify({
        "message": "Color service is running",
        "supported_colors": ["RED", "GREEN", "BLUE"]
    }), 200


if __name__ == "__main__":
    logger.info("REST API Service started at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
