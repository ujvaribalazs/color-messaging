
## RabbitMQ üzenetek szerkezete Python használatával (pika könyvtár)

### Üzenet fő komponensei

1. **Body** - Az üzenet törzse
   - Bármilyen tartalom lehet, általában byte-sorozat formában
   - Python esetében string-eket `encode()` metódussal alakítunk byte-sorozattá
   - Példa: `message_body = "Hello World".encode()`

2. **Headers** - Fejlécadatok
   - Kulcs-érték párok a headers exchange-hez
   - A `properties` részeként adjuk meg
   - Opcionális

3. **Routing Key** - Útválasztó kulcs
   - Meghatározza, hogy az üzenet mely várólá(nco)kba kerüljön
   - Direct és topic exchange-eknél különösen fontos
   - String érték

4. **Exchange** - Üzenetirányító
   - Meghatározza, hova továbbítja az üzenetet
   - Főbb típusok: direct, topic, fanout, headers

### Properties (BasicProperties)

A Pika könyvtárban a `pika.BasicProperties` objektumban definiáljuk:

```python
import pika

properties = pika.BasicProperties(
    content_type='text/plain',  # MIME típus
    content_encoding='utf-8',   # Kódolás
    headers={'x-custom-header': 'value'},  # Egyéni fejlécek
    delivery_mode=2,     # 2 = persistent (tartós), 1 = transient (átmeneti)
    priority=0,          # Üzenet prioritása (0-9)
    correlation_id='123', # Kérés-válasz azonosító
    reply_to='reply_queue', # Válasz várólistája
    expiration='60000',   # TTL milliszekundumban
    message_id='unique_id', # Egyedi üzenetazonosító
    timestamp=1234567890, # Unix timestamp
    type='message_type',  # Üzenet típusa
    user_id='guest',      # Küldő felhasználó
    app_id='my_app',      # Alkalmazás azonosító
    cluster_id='',        # Klaszter azonosító (ritkán használt)
)
```

### Teljes példa üzenet küldése

```python
import pika

# Kapcsolat létrehozása
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Exchange és queue deklarálása
channel.exchange_declare(exchange='logs', exchange_type='topic')
channel.queue_declare(queue='my_queue', durable=True)
channel.queue_bind(exchange='logs', queue='my_queue', routing_key='info.#')

# Üzenet tulajdonságok
properties = pika.BasicProperties(
    content_type='application/json',
    delivery_mode=2,  # persistent
    headers={'source': 'backend_service', 'importance': 'high'},
    message_id='msg-123',
    timestamp=123456789,
    app_id='my_application'
)

# Üzenet küldése
message_body = '{"status": "success", "data": {"id": 123}}'.encode()
routing_key = 'info.user.created'

channel.basic_publish(
    exchange='logs',
    routing_key=routing_key,
    body=message_body,
    properties=properties
)

connection.close()
```

### Üzenet fogadása

```python
def callback(ch, method, properties, body):
    print(f"Routing key: {method.routing_key}")
    print(f"Exchange: {method.exchange}")
    
    print(f"Content type: {properties.content_type}")
    print(f"Headers: {properties.headers}")
    print(f"Delivery mode: {properties.delivery_mode}")
    
    print(f"Message body: {body.decode()}")

channel.basic_consume(
    queue='my_queue',
    on_message_callback=callback,
    auto_ack=True
)

channel.start_consuming()
```

Ez az összefoglaló remélhetőleg jó emlékeztető lesz a RabbitMQ üzenetek szerkezetéről és azok Python-beli használatáról a pika könyvtárral!

RabbitMQ-ban az üzenet továbbítása a fogyasztók (consumer) felé két fő módszer alapján történhet:

### Routing Key alapján (Direct és Topic Exchange)

1. **Direct Exchange esetén**:
   - Az üzenet csak ahhoz a várólistához (queue) kerül, amelynek a binding key-je pontosan megegyezik a routing key-vel.
   - Példa: ha a publisher `user.created` routing key-vel küld, csak azok a queue-k kapják meg, amelyek pontosan erre a kulcsra iratkoztak fel.

2. **Topic Exchange esetén**:
   - Mintaillesztést használ, ahol a `*` egy szót helyettesít, a `#` pedig nulla vagy több szót.
   - Példa: ha a publisher `user.created` routing key-vel küld, akkor azt megkaphatják az olyan queue-k, amelyek `user.*` vagy `#.created` vagy `#` mintára iratkoztak fel.

### Header alapján (Headers Exchange)

- Itt nem a routing key számít, hanem a headers tulajdonságban megadott kulcs-érték párok.
- A fogyasztó meghatározza, mely fejléc értékekre szeretne szűrni.
- Két mód létezik:
  - `all` (x-match=all): minden megadott fejlécnek egyeznie kell
  - `any` (x-match=any): elég, ha egy fejléc egyezik

Példa headers exchange használatára:

```python
# Publisher
properties = pika.BasicProperties(
    headers={'format': 'pdf', 'type': 'report', 'x-match': 'all'}
)

channel.basic_publish(
    exchange='headers_exchange',
    routing_key='',  # Headers exchange esetén ez általában üres
    body=message_body,
    properties=properties
)

# Consumer binding
channel.queue_bind(
    exchange='headers_exchange',
    queue='pdf_reports',
    arguments={'x-match': 'all', 'format': 'pdf', 'type': 'report'}
)
```

Ebben a példában csak azok a fogyasztók kapják meg az üzenetet, akik pontosan ezekre a fejléc értékekre iratkoztak fel (mindkét értéknek egyeznie kell, mert `x-match=all`).

Tehát valóban, a RabbitMQ biztosítja, hogy az üzenetek csak a megfelelő, az adott routing pattern-re vagy header-értékekre feliratkozott fogyasztókhoz jussanak el, ezáltal lehetővé téve a célzott üzenettovábbítást.