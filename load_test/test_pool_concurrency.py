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

    total = time.monotonic() - start
    checkout = checkout_done - start

    return i, total, checkout


overall_start = time.monotonic()

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(work, range(10)))

overall = time.monotonic() - overall_start

print()
print(f"TOTAL: {overall:.3f}s")
print()

for i, total, checkout in results:
    print(
        f"User {i + 1}: "
        f"total={total:.3f}s "
        f"checkout={checkout:.3f}s"
    )
