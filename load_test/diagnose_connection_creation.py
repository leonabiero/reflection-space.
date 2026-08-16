from dotenv import load_dotenv
load_dotenv(r".\load_test\.env")

import os
import time
import psycopg2

url = os.getenv("DATABASE_URL")

print("DATABASE_URL loaded:", bool(url))
print()

conns = []
overall_start = time.monotonic()

for i in range(10):
    start = time.monotonic()

    try:
        conn = psycopg2.connect(url)
        elapsed = time.monotonic() - start
        conns.append(conn)

        print(f"Connection {i + 1}: {elapsed:.3f}s")
    except Exception as e:
        elapsed = time.monotonic() - start
        print(f"Connection {i + 1}: FAILED after {elapsed:.3f}s")
        print(type(e).__name__, str(e))

overall_elapsed = time.monotonic() - overall_start

print()
print(f"TOTAL: {overall_elapsed:.3f}s")

for conn in conns:
    conn.close()
