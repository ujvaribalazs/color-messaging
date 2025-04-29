Szívesen leírom a RabbitMQ alapvető komponenseinek (Exchange, Queue és Channel) szerkezetét és tulajdonságait.

## RabbitMQ komponensek szerkezete

### 1. Exchange szerkezete és tulajdonságai

```python
# Exchange deklarálása
channel.exchange_declare(
    exchange='my_exchange',      # Exchange neve (kötelező)
    exchange_type='direct',      # Típusa: direct, topic, fanout, headers
    passive=False,               # Csak ellenőrzés, nem hozza létre ha nem létezik
    durable=True,                # Túléli-e a broker újraindítását
    auto_delete=False,           # Törlődik-e, ha már nincs hozzá kapcsolódó queue
    internal=False,              # Csak belső használatra (más exchange-ek számára)
    arguments={                  # Opcionális tulajdonságok
        'alternate-exchange': 'unroutable_exchange',  # Ha nem routolható az üzenet
        'x-delayed-type': 'direct'                    # Delayed message plugin esetén
    }
)
```

#### Exchange típusok
- **Direct**: Pontos routing key egyezés alapján
- **Topic**: Mintaillesztés a routing key-ben (* = egy szó, # = 0+ szó)
- **Fanout**: Minden kapcsolódó queue-nak továbbít
- **Headers**: Fejléc értékek alapján továbbít, nem routing key alapján

### 2. Queue (Sor) szerkezete és tulajdonságai

```python
# Queue deklarálása
channel.queue_declare(
    queue='my_queue',           # Queue neve (ha üres, generált nevet kap)
    passive=False,              # Csak ellenőrzés, nem hozza létre ha nem létezik
    durable=True,               # Túléli-e a broker újraindítását
    exclusive=False,            # Csak a létrehozó kapcsolat használhatja
    auto_delete=False,          # Törlődik-e, ha már nincs fogyasztója
    arguments={                 # Opcionális tulajdonságok
        'x-message-ttl': 60000,             # Üzenetek élettartama (ms)
        'x-expires': 1800000,               # Queue élettartama (ms)
        'x-max-length': 1000,               # Max üzenetek száma
        'x-max-length-bytes': 10485760,     # Max méret bájtban
        'x-overflow': 'reject-publish',     # Mi történjen túlcsorduláskor (reject-publish, drop-head)
        'x-dead-letter-exchange': 'dlx',    # DL exchange neve
        'x-dead-letter-routing-key': 'dl',  # DL routing key
        'x-queue-mode': 'lazy',             # Lazy queue (lemezre ment ha lehet)
        'x-queue-type': 'classic',          # Queue típus (classic, quorum, stream)
        'x-max-priority': 10,               # Max prioritás (0-255)
        'x-single-active-consumer': True    # Csak egy aktív fogyasztó lehet
    }
)
```

#### Queue binding (kapcsolat az Exchange-hez)

```python
channel.queue_bind(
    queue='my_queue',           # Queue neve
    exchange='my_exchange',     # Exchange neve
    routing_key='routing.key',  # Routing kulcs
    arguments={                 # Opcionális argumentumok
        'x-match': 'all',       # Headers exchange esetén: all/any
        'format': 'pdf',        # Headers exchange paraméter
        'type': 'report'        # Headers exchange paraméter
    }
)
```

### 3. Channel (Csatorna) szerkezete

A Channel egy virtuális kapcsolat a RabbitMQ brokerhez egy fizikai TCP kapcsolaton belül.

```python
# Csatorna létrehozása
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# Csatorna beállítások
channel.basic_qos(
    prefetch_count=10,   # Egyszerre max ennyi üzenetet küld a consumer-nek
    prefetch_size=0,     # 0 = nincs korlátozás méret alapján
    global_qos=False     # False = csak erre a csatornára vonatkozik
)

# Tranzakciók kezelése
channel.tx_select()      # Tranzakciós mód bekapcsolása
channel.tx_commit()      # Tranzakció véglegesítése
channel.tx_rollback()    # Tranzakció visszagörgetése

# Publisher confirms
channel.confirm_delivery()  # Confirm mód bekapcsolása
```

#### Channel fogyasztói beállítások

```python
channel.basic_consume(
    queue='my_queue',                # Queue neve
    on_message_callback=callback,    # Callback függvény
    auto_ack=False,                  # Automatikus nyugtázás
    exclusive=False,                 # Kizárólagos fogyasztó
    consumer_tag='consumer_1',       # Fogyasztó azonosítója
    arguments={                      # Extra paraméterek
        'x-priority': 10             # Fogyasztó prioritása
    }
)
```

#### Consumer nyugtázás

```python
# Pozitív nyugtázás
channel.basic_ack(
    delivery_tag=method.delivery_tag,  # Üzenet azonosítója
    multiple=False                     # Több üzenet nyugtázása egyszerre
)

# Negatív nyugtázás (visszautasítás)
channel.basic_nack(
    delivery_tag=method.delivery_tag,  # Üzenet azonosítója
    multiple=False,                    # Több üzenet egyszerre
    requeue=False                      # False = DLX-re kerül, True = visszakerül a sorba
)

# Visszautasítás (régebbi alternatíva)
channel.basic_reject(
    delivery_tag=method.delivery_tag,  # Üzenet azonosítója
    requeue=False                      # False = DLX-re kerül, True = visszakerül a sorba
)
```

Ezek a struktúrák és tulajdonságok adják a RabbitMQ rendszer alapvető komponenseit. Természetesen vannak további komplexebb konfigurációs lehetőségek és plugin-specifikus beállítások is, de ez a leírás lefedi a legfontosabb elemeket.