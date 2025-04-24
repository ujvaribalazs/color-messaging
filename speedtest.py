import time
import threading
import multiprocessing
import asyncio
import queue
import random

# Közös konstansok
NUM_MESSAGES = 10000
COLORS = ["RED", "GREEN", "BLUE"]


def generate_messages():
    """10,000 színüzenet generálása teszteléshez"""
    return [random.choice(COLORS) for _ in range(NUM_MESSAGES)]


# 1. Threading megoldás tesztelése
def threading_test(messages):
    results = {"RED": 0, "GREEN": 0, "BLUE": 0}
    processed = 0

    def worker(color, message_queue, results_dict):
        while not message_queue.empty():
            try:
                message = message_queue.get(block=False)
                if message == color:
                    results_dict[color] += 1
                message_queue.task_done()
            except queue.Empty:
                break

    # Üzenetek queue-ba helyezése
    message_queue = queue.Queue()
    for msg in messages:
        message_queue.put(msg)

    # Szálak indítása
    threads = []
    for color in COLORS:
        thread = threading.Thread(target=worker, args=(color, message_queue, results))
        threads.append(thread)
        thread.start()

    # Várunk a befejezésre
    for thread in threads:
        thread.join()

    return results


# 2. Multiprocessing megoldás tesztelése
def multiprocessing_test(messages):
    # Megosztott értékek a folyamatok között
    manager = multiprocessing.Manager()
    results = manager.dict({"RED": 0, "GREEN": 0, "BLUE": 0})
    message_queue = manager.Queue()

    # Üzenetek queue-ba helyezése
    for msg in messages:
        message_queue.put(msg)

    def worker(color, message_queue, results_dict):
        while True:
            try:
                message = message_queue.get(block=False)
                if message == color:
                    results_dict[color] += 1
            except queue.Empty:
                break

    # Folyamatok indítása
    processes = []
    for color in COLORS:
        process = multiprocessing.Process(target=worker, args=(color, message_queue, results))
        processes.append(process)
        process.start()

    # Várunk a befejezésre
    for process in processes:
        process.join()

    return dict(results)


# 3. Asyncio megoldás tesztelése
async def asyncio_test(messages):
    results = {"RED": 0, "GREEN": 0, "BLUE": 0}

    async def worker(color, message_list, results_dict):
        for message in message_list:
            if message == color:
                results_dict[color] += 1
            # Szimuláljuk az I/O műveletet
            await asyncio.sleep(0.0001)

    # Taszkok indítása
    tasks = []
    for color in COLORS:
        task = asyncio.create_task(worker(color, messages, results))
        tasks.append(task)

    # Várunk a befejezésre
    await asyncio.gather(*tasks)

    return results


# Főprogram
def run_benchmarks():
    messages = generate_messages()

    print("=== Teljesítmény összehasonlítás ===")

    # Threading teszt
    start_time = time.time()
    threading_results = threading_test(messages)
    threading_time = time.time() - start_time
    print(f"Threading: {threading_time:.3f} másodperc, Eredmények: {threading_results}")

    # Multiprocessing teszt
    start_time = time.time()
    multiprocessing_results = multiprocessing_test(messages)
    multiprocessing_time = time.time() - start_time
    print(f"Multiprocessing: {multiprocessing_time:.3f} másodperc, Eredmények: {multiprocessing_results}")

    # Asyncio teszt
    start_time = time.time()
    asyncio_results = asyncio.run(asyncio_test(messages))
    asyncio_time = time.time() - start_time
    print(f"Asyncio: {asyncio_time:.3f} másodperc, Eredmények: {asyncio_results}")

    # Összehasonlítás
    print("\n=== Összehasonlítás ===")
    print(f"Threading: x{multiprocessing_time / threading_time:.2f} gyorsabb, mint Multiprocessing")
    print(f"Threading: x{asyncio_time / threading_time:.2f} gyorsabb, mint Asyncio")
    print(f"Multiprocessing: x{asyncio_time / multiprocessing_time:.2f} gyorsabb, mint Asyncio")


if __name__ == "__main__":
    run_benchmarks()