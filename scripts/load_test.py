import asyncio
import httpx
import time
import random
from datetime import datetime

URL = "http://127.0.0.1:8000/connections"

TARGET_RPS = 150
DURATION_SECONDS = 10

# Stats
total_requests = 0
total_success = 0
total_errors = 0
pending_ai_count = 0

latencies = []


def random_ip():
    return f"192.168.{random.randint(0,255)}.{random.randint(1,254)}"


def build_payload():
    return {
        "source_ip": random_ip(),
        "destination_ip": random_ip(),
        "destination_port": random.choice([80, 443, 22, 8080]),
        "protocol": random.choice(["TCP", "UDP"]),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


async def send_request(client):

    global total_requests, total_success, total_errors, pending_ai_count

    payload = build_payload()

    start = time.perf_counter()

    try:

        response = await client.post(URL, json=payload)

        latency = time.perf_counter() - start

        latencies.append(latency)

        total_requests += 1

        if response.status_code == 200:

            total_success += 1

            data = response.json()

            if data.get("pending_ai") is True:
                pending_ai_count += 1

        else:
            total_errors += 1

    except Exception:
        total_errors += 1


async def worker(client, requests_per_worker):

    tasks = []

    for _ in range(requests_per_worker):
        tasks.append(send_request(client))

    await asyncio.gather(*tasks)


async def run_test():

    async with httpx.AsyncClient(timeout=10.0) as client:

        start_time = time.time()

        interval = 1.0

        while time.time() - start_time < DURATION_SECONDS:

            batch_start = time.time()

            await worker(client, TARGET_RPS)

            elapsed = time.time() - batch_start

            sleep_time = max(0, interval - elapsed)

            await asyncio.sleep(sleep_time)


def print_stats():

    print("\n=== Load Test Results ===")

    print(f"Total requests: {total_requests}")
    print(f"Success: {total_success}")
    print(f"Errors: {total_errors}")

    if total_success > 0:
        print(f"Pending AI: {pending_ai_count} ({pending_ai_count/total_success*100:.1f}%)")

    if latencies:
        print(f"Avg latency: {sum(latencies)/len(latencies):.4f} sec")
        print(f"Max latency: {max(latencies):.4f} sec")
        print(f"Min latency: {min(latencies):.4f} sec")


if __name__ == "__main__":

    print(f"Running load test: {TARGET_RPS} req/sec for {DURATION_SECONDS} seconds")

    asyncio.run(run_test())

    print_stats()