import json

import pytest

from experiments import run_experiment as experiment


def test_synthetic_instance_covers_every_ordered_pair():
    instance = experiment.synthetic_instance(6, seed=1)

    pairs = {(leg.from_index, leg.to_index) for leg in instance.legs}

    assert len(pairs) == 6 * 5
    assert instance.vehicle_mass_kg == 7500.0


def test_synthetic_slopes_are_opposite_in_each_direction():
    instance = experiment.synthetic_instance(6, seed=1)
    legs = {(leg.from_index, leg.to_index): leg for leg in instance.legs}

    for (a, b), leg in legs.items():
        assert leg.slope_percent == pytest.approx(-legs[(b, a)].slope_percent)
        assert abs(leg.slope_percent) <= experiment.MAX_SLOPE_PERCENT
        assert leg.speed_kmh == pytest.approx(legs[(b, a)].speed_kmh)


def test_synthetic_instance_is_reproducible():
    first = experiment.synthetic_instance(5, seed=3)
    second = experiment.synthetic_instance(5, seed=3)

    assert first.legs == second.legs


def test_load_instance_reads_the_optimize_request_format(tmp_path):
    path = tmp_path / "centro-03.json"
    segments = [
        {"from_index": a, "to_index": b, "distance_meters": 1000.0, "average_speed_kmh": 30.0, "slope_percent": 1.0}
        for a in range(3) for b in range(3) if a != b
    ]
    path.write_text(json.dumps({"vehicle_mass_kg": 7500, "point_count": 3, "segments": segments}))

    instance = experiment.load_instance(path)

    assert instance.name == "centro-03"
    assert instance.point_count == 3
    assert instance.legs[0].distance_km == pytest.approx(1.0)
    assert instance.load_ratio == 1.0


def test_run_instance_never_lets_emission_criterion_emit_more_on_a_small_instance():
    rows = experiment.run_instance(experiment.synthetic_instance(7, seed=2), seeds=(1,))

    assert rows[0]["e_emission_kg"] <= rows[0]["e_distance_kg"] + 1e-9
    assert rows[0]["delta_percent"] >= -1e-9


def test_summary_applies_the_five_percent_in_four_of_five_rule():
    def row(name, delta):
        return {
            "instance": name, "points": 10, "e_distance_kg": 1.0, "e_emission_kg": 1.0 - delta / 100,
            "delta_percent": delta, "seconds_distance": 1.0, "seconds_emission": 2.0,
        }

    rows = [row("a", 6), row("a", 4), row("b", 10), row("c", 5), row("d", 7), row("e", 1)]

    summary = experiment.summarize(rows)

    assert [i["meets_target"] for i in summary["instances"]] == [True, True, True, True, False]
    assert summary["instances"][0]["mean_delta_percent"] == pytest.approx(5.0)
    assert summary["experiment_passes"] is True
    assert summary["all_under_60_seconds"] is True


def test_main_writes_results_for_instances_from_a_folder(tmp_path, monkeypatch):
    instances_dir = tmp_path / "instancias"
    instances_dir.mkdir()
    instance = experiment.synthetic_instance(5, seed=1)
    segments = [
        {"from_index": l.from_index, "to_index": l.to_index, "distance_meters": l.distance_km * 1000,
         "average_speed_kmh": l.speed_kmh, "slope_percent": l.slope_percent}
        for l in instance.legs
    ]
    (instances_dir / "pequena.json").write_text(
        json.dumps({"vehicle_mass_kg": 7500, "point_count": 5, "segments": segments})
    )
    monkeypatch.setattr(experiment, "SEEDS", (1,))
    monkeypatch.setattr(experiment.run_instance, "__defaults__", ((1,),))

    summary = experiment.main(["--instances-dir", str(instances_dir), "--output-dir", str(tmp_path / "out")])

    assert summary["instances"][0]["instance"] == "pequena"
    assert (tmp_path / "out" / "execucoes.csv").exists()
    assert json.loads((tmp_path / "out" / "resumo.json").read_text())["optimizer_version"] == "0.1.0"
