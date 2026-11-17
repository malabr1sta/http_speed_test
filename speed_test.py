#!/usr/bin/env python3
"""Usage: python speed_test.py URL [--timeout 30]

Measure ten sequential HTTP downloads. Counts response body bytes only.
Timeout limits individual blocking socket operations, not the whole download.
Stops on the first error instead of reporting an incomplete average.
"""

import argparse
import math
import sys
import time
from http.client import HTTPException
from typing import Tuple
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

REQUEST_COUNT = 10
CHUNK_SIZE = 64 * 1024


def positive_timeout(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Тайм-аут должен быть положительным числом")
    return number


def download(url: str, timeout: float) -> Tuple[float, int]:
    request = Request(url, headers={"Accept-Encoding": "identity"})
    size = 0
    start = time.perf_counter()
    with urlopen(request, timeout=timeout) as response:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
        # A sized read may reach EOF without raising IncompleteRead.
        if response.length not in (None, 0):
            raise OSError("Ответ оборвался до получения полного тела")
    return time.perf_counter() - start, size


def main() -> int:
    parser = argparse.ArgumentParser(
        description="10 последовательных скачиваний: среднее время и общий объём."
    )
    parser.add_argument("url", help="Адрес файла (http:// или https://)")
    parser.add_argument("--timeout", type=positive_timeout, default=30,
                        help="Тайм-аут сетевой операции в секундах (по умолчанию 30)")
    args = parser.parse_args()
    try:
        parsed = urlsplit(args.url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            parser.error("Укажите корректный HTTP(S)-адрес")
    except ValueError as exc:
        parser.error(str(exc))

    total_time = 0.0
    total_bytes = 0
    for index in range(1, REQUEST_COUNT + 1):
        try:
            elapsed, size = download(args.url, args.timeout)
        except (URLError, OSError, HTTPException, ValueError) as exc:
            print(f"Запрос {index}/{REQUEST_COUNT}: ошибка: {exc}", file=sys.stderr)
            return 1
        total_time += elapsed
        total_bytes += size
        print(f"{index:2}/{REQUEST_COUNT}: {elapsed:.3f} с, {size} байт", flush=True)

    print(f"\nСреднее время запроса: {total_time / REQUEST_COUNT:.3f} с")
    print(f"Всего скачано: {total_bytes} байт ({total_bytes / 1024**2:.2f} МиБ)")
    speed_mbps = total_bytes * 8 / total_time / 1_000_000 if total_time else 0.0
    print(f"Средняя скорость скачивания: {speed_mbps:.3f} Мбит/с")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nИзмерение прервано.", file=sys.stderr)
        sys.exit(130)
