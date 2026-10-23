"""QZ-02: p95 response times of the list endpoints against a running stack.

Usage: start the stack (``docker compose up --build``), seed the test accounts
(``mise run seed``), then ``mise run measure``. Prompts for the password of the test account.
Every endpoint gets one warm-up call and 30 timed calls; the p95 must stay at or below
2 seconds, otherwise the exit code is 1. The Markdown table goes into the test report.

Plain http needs APP_ENV=development (set by compose.override.yaml): httpx does not send the
Secure session cookie of the other environments over http.
"""

import getpass
import math
import platform
import statistics
import sys
import time

import httpx

API = "http://localhost:8000/api/v1"
ACCOUNT = "test1@example.org"
RUNS = 30
LIMIT_SECONDS = 2.0


def p95(seconds: list[float]) -> float:
    """95th percentile by nearest rank: the 29th of 30 sorted values."""
    return sorted(seconds)[math.ceil(0.95 * len(seconds)) - 1]


def measure(client: httpx.Client, path: str) -> list[float]:
    """Call `path` once to warm up, then RUNS times with the time of each call."""
    client.get(path).raise_for_status()
    seconds: list[float] = []
    for _ in range(RUNS):
        start = time.perf_counter()
        client.get(path).raise_for_status()
        seconds.append(time.perf_counter() - start)
    return seconds


def busiest_person(client: httpx.Client) -> str:
    """ID of the person whose view (F-09) holds the most entries: the worst case."""
    people = client.get("/people", params={"limit": 200}).raise_for_status().json()["items"]

    def entries(person_id: str) -> int:
        view = client.get(f"/people/{person_id}/overview").raise_for_status().json()
        return sum(section["total"] for section in view.values())

    return max((person["id"] for person in people), key=entries)


def main() -> int:
    """Measure every list endpoint, print the table and return the exit code."""
    password = getpass.getpass(f"Password for {ACCOUNT}: ")
    with httpx.Client(base_url=API, timeout=30) as client:
        client.post("/auth/login", json={"email": ACCOUNT, "password": password}).raise_for_status()
        paths = [
            "/full-list",
            "/people?limit=200",
            "/occasions?limit=200",
            "/gifts?limit=200",
            "/giftings?limit=200",
            "/tasks?limit=200",
            f"/people/{busiest_person(client)}/overview?limit=200",
        ]
        print(f"QZ-02 against {API}: {RUNS} timed calls per endpoint after one warm-up.")
        print(f"Machine: {platform.platform()}, Python {platform.python_version()}.\n")
        print("| Endpoint | Median | p95 | Max | p95 ≤ 2 s |")
        print("| --- | --- | --- | --- | --- |")
        passed = True
        for path in paths:
            seconds = measure(client, path)
            ok = p95(seconds) <= LIMIT_SECONDS
            passed = passed and ok
            print(
                f"| `{path}` | {statistics.median(seconds) * 1000:.0f} ms "
                f"| {p95(seconds) * 1000:.0f} ms | {max(seconds) * 1000:.0f} ms "
                f"| {'yes' if ok else 'NO'} |"
            )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
