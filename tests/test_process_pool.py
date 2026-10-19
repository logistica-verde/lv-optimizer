import threading
from concurrent.futures.process import BrokenProcessPool

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.optimization import process_pool
from tests.test_optimize_api import make_request

client = TestClient(app)


def test_the_number_of_processes_defaults_to_the_cpus_up_to_a_cap(monkeypatch):
    monkeypatch.delenv("OPTIMIZER_PROCESSES", raising=False)
    monkeypatch.setattr(process_pool.os, "cpu_count", lambda: 16)

    assert process_pool.process_count() == process_pool.DEFAULT_MAX_PROCESSES


def test_a_machine_with_one_cpu_gets_one_process(monkeypatch):
    monkeypatch.delenv("OPTIMIZER_PROCESSES", raising=False)
    monkeypatch.setattr(process_pool.os, "cpu_count", lambda: 1)

    assert process_pool.process_count() == 1
    monkeypatch.setattr(process_pool.os, "cpu_count", lambda: None)
    assert process_pool.process_count() == 1


def test_the_number_of_processes_can_be_set_by_the_environment(monkeypatch):
    monkeypatch.setenv("OPTIMIZER_PROCESSES", "6")

    assert process_pool.process_count() == 6


@pytest.mark.parametrize("value", ["", "0", "-2", "abc", "1.5"])
def test_an_invalid_setting_falls_back_to_the_default(monkeypatch, value):
    monkeypatch.setenv("OPTIMIZER_PROCESSES", value)
    monkeypatch.setattr(process_pool.os, "cpu_count", lambda: 8)

    assert process_pool.process_count() == process_pool.DEFAULT_MAX_PROCESSES


def test_the_pool_is_created_once_and_can_be_reset():
    process_pool.reset_pool()

    first = process_pool.get_pool()

    assert process_pool.get_pool() is first
    process_pool.reset_pool()
    assert process_pool.get_pool() is not first


def test_the_pool_starts_its_processes_with_spawn_to_avoid_forking_a_busy_server():
    process_pool.reset_pool()

    assert process_pool.get_pool()._mp_context.get_start_method() == "spawn"


def test_warming_up_starts_the_processes_before_the_first_request(monkeypatch):
    monkeypatch.setenv("OPTIMIZER_PROCESSES", "2")
    process_pool.reset_pool()

    pids = process_pool.warm_up()

    assert len(pids) == 2
    assert all(pid > 0 for pid in pids)


def test_the_application_warms_the_pool_up_when_it_starts(monkeypatch):
    monkeypatch.setenv("OPTIMIZER_PROCESSES", "2")
    process_pool.reset_pool()

    with TestClient(app) as started:
        assert started.get("/health").status_code == 200
        assert process_pool._pool is not None

    assert process_pool._pool is None


def test_the_same_request_gives_the_same_route_in_the_pool():
    body = make_request(9, criterion="emission")

    first = client.post("/optimize", json=body).json()
    second = client.post("/optimize", json=body).json()

    assert first["sequence"] == second["sequence"]
    assert first["total_emission_kg"] == second["total_emission_kg"]


def test_simultaneous_requests_all_finish_with_the_right_answer():
    bodies = [make_request(8, criterion=criterion, seed=seed) for criterion in ("emission", "distance") for seed in (3, 4)]
    alone = [client.post("/optimize", json=body).json() for body in bodies]
    together = [None] * len(bodies)

    def ask(index):
        together[index] = client.post("/optimize", json=bodies[index]).json()

    threads = [threading.Thread(target=ask, args=(index,)) for index in range(len(bodies))]
    [thread.start() for thread in threads]
    [thread.join() for thread in threads]

    assert [answer["sequence"] for answer in together] == [answer["sequence"] for answer in alone]


class BrokenPool:
    def submit(self, *_args, **_kwargs):
        raise BrokenProcessPool("a worker died")

    def shutdown(self, *_args, **_kwargs):
        return None


def test_a_broken_pool_is_replaced_for_the_next_request(monkeypatch):
    process_pool.reset_pool()
    monkeypatch.setattr(process_pool, "_pool", BrokenPool())
    failing = TestClient(app, raise_server_exceptions=False)

    answer = failing.post("/optimize", json=make_request(6))

    assert answer.status_code == 500
    assert process_pool._pool is None
    assert client.post("/optimize", json=make_request(6)).status_code == 200
