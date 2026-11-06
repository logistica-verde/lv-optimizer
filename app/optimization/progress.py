"""Progress of an optimization that runs in a worker process, sent back to the API process."""

import queue
import time
from collections.abc import Callable
from typing import Protocol

from app.optimization.route_optimizer import RouteResult

REPORT_INTERVAL_S = 0.2


class ProgressQueue(Protocol):
    def put(self, item: tuple[int, int]) -> None: ...

    def get_nowait(self) -> tuple[int, int]: ...


def throttled_reporter(
    progress: ProgressQueue, interval_s: float = REPORT_INTERVAL_S, clock: Callable[[], float] = time.monotonic
) -> Callable[[int, int], None]:
    """Callback for GeneticAlgorithm.evolve that sends (generation, generations) at most once per interval.

    The first and the last generation are always sent."""
    last_sent: float | None = None

    def report(generation: int, generations: int) -> None:
        nonlocal last_sent
        now = clock()
        if last_sent is None or generation >= generations or now - last_sent >= interval_s:
            last_sent = now
            progress.put((generation, generations))

    return report


def optimize_reporting_progress(progress: ProgressQueue, solve: Callable[..., RouteResult]) -> RouteResult:
    """Runs in the worker process: solve is optimize_route with every argument but on_generation bound."""
    return solve(on_generation=throttled_reporter(progress))


def latest(progress: ProgressQueue) -> tuple[int, int] | None:
    """Most recent progress waiting in the queue, discarding the older ones."""
    newest = None
    while True:
        try:
            newest = progress.get_nowait()
        except queue.Empty:
            return newest
