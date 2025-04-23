import subprocess
import time
import logging
import sys
import signal

# Beállítjuk a naplózást
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("starter")

processes = []


def start_service(module_name, process_name):
    """
    Elindít egy szolgáltatást külön folyamatban.

    :param module_name: A futtatandó Python modul neve
    :param process_name: A folyamat megnevezése a logokban
    :return: A folyamat referenciája
    """
    logger.info(f"Starting {process_name}...")
    process = subprocess.Popen([sys.executable, module_name],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True)
    logger.info(f"{process_name} started with PID: {process.pid}")
    return process


def cleanup():
    """
    Leállítja az összes elindított folyamatot.
    """
    logger.info("Stopping all processes...")
    for process in processes:
        if process.poll() is None:  # Ha még fut a folyamat
            logger.info(f"Terminating process with PID: {process.pid}")
            process.terminate()

    # Várjuk meg, hogy minden folyamat leálljon
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"Process with PID {process.pid} did not terminate gracefully, killing it...")
            process.kill()

    logger.info("All processes stopped")
    sys.exit(0)


def main():
    """
    Elindítja az összes szolgáltatást megfelelő sorrendben.
    """
    # Jelkezelők beállítása a megfelelő leállításhoz
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        # Ellenőrizzük, hogy fut-e RabbitMQ
        logger.info("Make sure RabbitMQ is running on localhost:5672")
        logger.info(
            "If not, start it with 'docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management'")

        # Először elindítjuk a SOAP szolgáltatást
        soap_process = start_service("soap_service.py", "SOAP Service")
        processes.append(soap_process)

        # Várunk egy kicsit, hogy a szolgáltatás elinduljon
        logger.info("Waiting for SOAP service to start...")
        time.sleep(5)

        # Elindítjuk az üzenetfeldolgozókat
        red_process = start_service("mdb_red.py", "Red Message Processor")
        processes.append(red_process)

        green_process = start_service("mdb_green.py", "Green Message Processor")
        processes.append(green_process)

        blue_process = start_service("mdb_blue.py", "Blue Message Processor")
        processes.append(blue_process)

        # Elindítjuk a statisztika klienst
        stats_process = start_service("statistics_client.py", "Statistics Client")
        processes.append(stats_process)

        # Végül elindítjuk a színgeneráló klienst
        producer_process = start_service("color_producer_soap.py", "Color Producer")
        processes.append(producer_process)

        logger.info("All services started. Press Ctrl+C to stop.")

        # Várunk, amíg a felhasználó megszakítja a futást
        while True:
            time.sleep(1)

            # Ellenőrizzük, hogy minden folyamat még fut-e
            for i, process in enumerate(processes):
                if process.poll() is not None:
                    logger.error(f"Process {process.pid} exited unexpectedly with return code {process.returncode}")
                    logger.error(f"STDOUT: {process.stdout.read()}")
                    logger.error(f"STDERR: {process.stderr.read()}")
                    cleanup()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
