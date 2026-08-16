from dotenv import load_dotenv
load_dotenv(r".\load_test\.env")

import time
import concurrent.futures
from services.db_pool import get_conn

def work(i):
    start = time.monotonic()

    conn = get_conn()
    checkout_done = time.monotonic()

    cur = conn.cursor()
    cur.execute("SELECT 1")
    cur.fetchone()
    conn.close()

    return i, time.monotonic() - start, checkout_done - start


def run_wave(number):
    start = time.monotonic()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(work, range(10)))

    elapsed = time.monotonic() - start

    print()
    print(f"===== WAVE {number} =====")
    print(f"TOTAL: {elapsed:.3f}s")

    for i, total, checkout in results:
        print(
            f"User {i + 1}: "
            f"total={total:.3f}s "
            f"checkout={checkout:.3f}s"
        )


print("Starting Wave 1...")
run_wave(1)

print()
print("Starting Wave 2...")
run_wave(2)
