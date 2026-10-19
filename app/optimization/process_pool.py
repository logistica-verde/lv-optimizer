import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

DEFAULT_MAX_PROCESSES = 4

_pool: ProcessPoolExecutor | None = None


def process_count() -> int:
    configured = os.getenv("OPTIMIZER_PROCESSES", "").strip()
    if configured.isdigit() and int(configured) >= 1:
        return int(configured)
    return max(1, min(DEFAULT_MAX_PROCESSES, os.cpu_count() or 1))


def get_pool() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ProcessPoolExecutor(
            max_workers=process_count(), mp_context=multiprocessing.get_context("spawn")
        )
    return _pool


def reset_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None


def _import_the_solver() -> int:
    from app.optimization import route_optimizer

    return os.getpid() if route_optimizer is not None else -1


def warm_up() -> list[int]:
    pool = get_pool()
    futures = [pool.submit(_import_the_solver) for _ in range(process_count())]
    return [future.result() for future in futures]
