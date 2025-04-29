
## 1. Módosítandó részek a meglévő kódban

### 1.1. Dead Letter Exchange konfiguráció

A meglévő `ColorMessageProcessor` osztályban módosítanunk kell a queue deklarálást, hogy támogassa a Dead Letter Exchange-et:

```python
# Queue létrehozása DLX konfigurációval
def __init__(self, color):
    # Meglévő kód...
    
    # Exchange beállítása
    self.channel.exchange_declare(exchange='color_exchange', exchange_type='direct')
    
    # Dead Letter Exchange létrehozása
    self.channel.exchange_declare(exchange='dlx', exchange_type='direct')
    self.channel.queue_declare(queue='DLQ', durable=True)
    self.channel.queue_bind(exchange='dlx', queue='DLQ', routing_key='#')
    
    # Üzenetsor létrehozása DLX konfigurációval
    self.channel.queue_declare(
        queue=self.queue_name,
        arguments={
            'x-dead-letter-exchange': 'dlx',
            'x-dead-letter-routing-key': 'dead.' + self.routing_key
        }
    )
    
    # Többi kód marad...
```

### 1.2. Véletlenszerű rollback implementálása

A `process_message` metódust módosítanunk kell a 30%-os véletlenszerű rollback megvalósításához:

```python
def process_message(self, ch, method, properties, body):
    import random
    
    message = body.decode('utf-8')
    logger.info(f"MDB {self.color} received message: {message}")
    
    # 30% eséllyel rollback-eljük az üzenetet (3 a 10-ből)
    if random.randint(1, 10) <= 3:
        logger.info(f"Rolling back message: {message}")
        # Negatív nyugtázás requeue=False paraméterrel -> Dead Letter Exchange-re kerül
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return
    
    # Feldolgozzuk az üzenetet
    self.message_count += 1
    logger.info(f"Successfully processed {self.color} message: {message}")
    
    # Nyugtázzuk az üzenet feldolgozását
    ch.basic_ack(delivery_tag=method.delivery_tag)
    
    # Ha elértük a 10 üzenetet, statisztikát küldünk
    if self.message_count % 10 == 0:
        self.send_statistics()
```

## 2. Új kliens a Dead Letter Queue figyelésére

Hozzunk létre egy új osztályt a DLQ figyelésére:

```python 
class DeadLetterQueueConsumer:
    def __init__(self):
        # Kapcsolódás a RabbitMQ-hoz
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            )
        )
        self.channel = self.connection.channel()
        
        # Ellenőrizzük, hogy a DLQ létezik-e
        self.channel.queue_declare(queue='DLQ', durable=True, passive=True)
        
        # Feliratkozunk a DLQ-ra
        self.channel.basic_consume(
            queue='DLQ',
            on_message_callback=self.process_dead_letter,
            auto_ack=True
        )
        
        logger.info("Dead Letter Queue Consumer started. Waiting for unprocessed messages...")
    
    def process_dead_letter(self, ch, method, properties, body):
        message = body.decode('utf-8')
        original_exchange = properties.headers.get('x-first-death-exchange', 'unknown')
        original_routing_key = properties.headers.get('x-first-death-queue', 'unknown')
        
        logger.warning(f"Dead Letter received: {message}")
        logger.warning(f"Original exchange: {original_exchange}, Original queue: {original_routing_key}")
        print(f"UNPROCESSED MESSAGE: {message} from queue {original_routing_key}")
    
    def start(self):
        self.channel.start_consuming()
    
    def stop(self):
        if self.connection.is_open:
            self.channel.stop_consuming()
            self.connection.close()
            logger.info("Dead Letter Queue Consumer connection closed")
```

## 3. Módosított főprogram, amely elindítja a DLQ fogyasztót is

```python
if __name__ == "__main__":
    # Létrehozzuk a három szálat a három színnek
    threads = []
    for color in ["RED", "GREEN", "BLUE"]:
        thread = threading.Thread(target=processor_thread, args=(color,))
        thread.daemon = True
        threads.append(thread)
        thread.start()
        logger.info(f"Started {color} processor thread")
    
    # Elindítjuk a Dead Letter Queue figyelőt
    def dlq_thread():
        consumer = DeadLetterQueueConsumer()
        try:
            consumer.start()
        except Exception as e:
            logger.error(f"Error in DLQ consumer: {e}")
        finally:
            consumer.stop()
    
    dl_thread = threading.Thread(target=dlq_thread)
    dl_thread.daemon = True
    dl_thread.start()
    logger.info("Started Dead Letter Queue consumer thread")
    
    # Várunk amíg a főprogram fut
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping all processors...")
    
    # Megvárjuk, hogy minden szál befejeződjön
    for thread in threads:
        thread.join(timeout=5)
    
    dl_thread.join(timeout=5)
    
    logger.info("All processors stopped")
```

## 4. Statisztikai kliens implementációja

Bár ez már részben megvalósult a kódodban (a statisztikai üzeneteket küldő rész), érdemes lenne egy külön klienst is létrehozni, ami figyeli a statisztika sort:

```python
class StatisticsConsumer:
    def __init__(self):
        # Kapcsolódás a RabbitMQ-hoz
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            )
        )
        self.channel = self.connection.channel()
        
        # Ellenőrizzük, hogy a statisztikai sor létezik-e
        self.channel.queue_declare(queue=STATISTICS_QUEUE)
        
        # Feliratkozunk a statisztikai sorra
        self.channel.basic_consume(
            queue=STATISTICS_QUEUE,
            on_message_callback=self.process_statistics,
            auto_ack=True
        )
        
        logger.info("Statistics Consumer started. Waiting for statistics messages...")
    
    def process_statistics(self, ch, method, properties, body):
        statistic = body.decode('utf-8')
        print(f"STATISTICS: {statistic}")
    
    def start(self):
        self.channel.start_consuming()
    
    def stop(self):
        if self.connection.is_open:
            self.channel.stop_consuming()
            self.connection.close()
            logger.info("Statistics Consumer connection closed")
```

És természetesen ezt is hozzá kell adni a főprogramhoz:

```python
# Elindítjuk a Statisztika figyelőt
def stats_thread():
    consumer = StatisticsConsumer()
    try:
        consumer.start()
    except Exception as e:
        logger.error(f"Error in Statistics consumer: {e}")
    finally:
        consumer.stop()

stats_thread = threading.Thread(target=stats_thread)
stats_thread.daemon = True
stats_thread.start()
logger.info("Started Statistics consumer thread")

# ...és hozzáadjuk a join-hoz is
stats_thread.join(timeout=5)
```

## Magyarázat a fő változtatásokhoz

1. **Dead Letter Exchange konfiguráció** - Létrehoztunk egy DLX exchange-et és egy DLQ sort, ahová a visszautasított üzenetek kerülnek
2. **Véletlenszerű rollback** - 30% eséllyel (3/10) visszautasítjuk az üzeneteket, amelyek így a DLQ-ra kerülnek
3. **DLQ fogyasztó** - Ez a kliens figyeli a DLQ-t és kijelzi a konzolon, ha egy üzenetet nem dolgoztak fel
4. **Statisztikai fogyasztó** - Bár a statisztika küldése már megvalósult, hozzáadtunk egy külön klienst, ami figyeli és kijelzi ezeket

A kód most már teljesíti a feladat minden követelményét: három kliens (színek szerint), véletlenszerű rollback, statisztika küldése és DLQ figyelése.