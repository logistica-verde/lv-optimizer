import json
import queue

from fastapi.testclient import TestClient

from app.main import app
from app.optimization.genetic_algorithm import GeneticAlgorithm
from app.optimization.progress import latest, throttled_reporter
from app.optimization.fitness.distance import DistanceFitnessFunction
from app.optimization.route_optimizer import build_matrices
from tests.test_optimize_api import make_request

client = TestClient(app)


def stream(body):
    response = client.post("/optimize/stream", json=body)
    return response, [json.loads(line) for line in response.text.splitlines() if line]


def test_streams_the_progress_and_ends_with_the_same_result_as_optimize():
    body = make_request(8, ga_params={"population_size": 30, "generations": 40})

    response, events = stream(body)
    streamed = events[-1]["result"]
    answered = client.post("/optimize", json=body).json()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert events[-1]["type"] == "result"
    streamed.pop("elapsed_seconds")
    answered.pop("elapsed_seconds")
    assert streamed == answered


def test_the_progress_starts_at_zero_counts_up_and_reaches_the_last_generation():
    body = make_request(8, ga_params={"population_size": 30, "generations": 40})

    _, events = stream(body)

    progress = [event for event in events if event["type"] == "progress"]
    generations = [event["generation"] for event in progress]
    assert progress[0] == {"type": "progress", "generation": 0, "generations": 40}
    assert generations == sorted(generations)
    assert generations[-1] == 40
    assert all(event["generations"] == 40 for event in progress)


def test_an_instance_without_a_genetic_search_still_answers_with_a_result():
    _, events = stream(make_request(2))

    assert events[-1]["type"] == "result"
    assert events[-1]["result"]["sequence"] == [0, 1]


def test_an_invalid_request_is_rejected_before_streaming():
    body = make_request(4)
    body["segments"] = body["segments"][1:]

    response = client.post("/optimize/stream", json=body)

    assert response.status_code == 422


def test_the_genetic_algorithm_reports_every_generation():
    distance, _, _ = build_matrices(5, [])
    reported = []
    ga = GeneticAlgorithm(DistanceFitnessFunction(distance), 4, population_size=10, generations=6, seed=1)

    _, run = ga.evolve(lambda generation, total: reported.append((generation, total)))

    assert reported == [(g, 6) for g in range(1, run + 1)]


def test_the_reporter_sends_the_first_and_last_generation_and_throttles_the_rest():
    sent = queue.Queue()
    now = [0.0]
    report = throttled_reporter(sent, interval_s=1.0, clock=lambda: now[0])

    for generation in range(1, 11):
        now[0] = generation * 0.3
        report(generation, 10)

    values = [sent.get_nowait()[0] for _ in range(sent.qsize())]
    assert values[0] == 1
    assert values[-1] == 10
    assert len(values) < 10


def test_latest_keeps_only_the_newest_progress():
    waiting = queue.Queue()
    for generation in (1, 2, 3):
        waiting.put((generation, 10))

    assert latest(waiting) == (3, 10)
    assert latest(waiting) is None
