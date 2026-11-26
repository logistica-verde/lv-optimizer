"""Recomputes the street matrices of the real-road trials (item L02).

Repeats, step by step, what the lv-api does before calling the optimizer (RoadNetworkSegmentSource,
SlopeCalculator, OsrmClient, ElevationClient and GeoPoint.snapped, unchanged since 2026-10-18):
for each ordered pair of points, the OSRM route gives the distance and the duration, the speed is
distance / duration clamped to 5-90 km/h, and the slope comes from the SRTM elevation of the route
geometry resampled every 100 m, smoothed over up to 3 samples at each end.

Only the standard library is used, so it runs inside the optimizer container, which is on the same
Docker network as OSRM and the elevation service:

    docker compose exec -T optimizer python - --points pontos.json < reproducao/matrizes_ruas_reais.py > pares.json
"""

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request

EARTH_RADIUS_METERS = 6_371_008.8
SAMPLE_STEP_METERS = 100.0
MIN_SPEED_KMH, MAX_SPEED_KMH, FALLBACK_SPEED_KMH = 5.0, 90.0, 30.0
MAX_GRADE_PERCENT, MIN_LENGTH_METERS, SMOOTHING_WINDOW = 15.0, 50.0, 3
ELEVATION_BATCH = 100


def haversine_m(lat1, lon1, lat2, lon2):
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) * math.sin(d_lat / 2)
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) * math.sin(d_lon / 2))
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def java_round(value):
    return math.floor(value + 0.5)


def snapped(point):
    return (java_round(point[0] * 10_000.0) / 10_000.0, java_round(point[1] * 10_000.0) / 10_000.0)


def resample(path, step):
    if len(path) < 2:
        return list(path)
    sampled = [path[0]]
    next_at, walked = step, 0.0
    for index in range(1, len(path)):
        start, end = path[index - 1], path[index]
        length = haversine_m(start[0], start[1], end[0], end[1])
        while length > 0 and walked + length >= next_at:
            fraction = (next_at - walked) / length
            sampled.append((start[0] + (end[0] - start[0]) * fraction, start[1] + (end[1] - start[1]) * fraction))
            next_at += step
        walked += length
    last = path[-1]
    if haversine_m(sampled[-1][0], sampled[-1][1], last[0], last[1]) > 1.0:
        sampled.append(last)
    return sampled


def slope_percent(elevations, length_m):
    known = next((value for value in elevations if value is not None), None)
    if known is None:
        return 0.0
    filled, previous = [], known
    for value in elevations:
        previous = previous if value is None else value
        filled.append(previous)
    if len(filled) < 2 or length_m < MIN_LENGTH_METERS:
        return 0.0
    count = len(filled)
    window = max(1, min(SMOOTHING_WINDOW, count // 3))
    start = sum(filled[:window]) / window
    end = sum(filled[count - window:]) / window
    effective = length_m * (count - window) / (count - 1)
    grade = (end - start) / effective * 100.0
    return max(-MAX_GRADE_PERCENT, min(MAX_GRADE_PERCENT, grade))


def java_double(value):
    text = repr(float(value))
    return text


def get_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read())


def osrm_route(base, start, end):
    coordinates = f"{java_double(start[1])},{java_double(start[0])};{java_double(end[1])},{java_double(end[0])}"
    data = get_json(f"{base}/route/v1/driving/{coordinates}?overview=full&geometries=geojson&steps=false")
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"OSRM sem rota entre {start} e {end}")
    route = data["routes"][0]
    return route["distance"], route["duration"], [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]


def elevations(base, points):
    found = {}
    unique = list(dict.fromkeys(points))
    for i in range(0, len(unique), ELEVATION_BATCH):
        batch = unique[i:i + ELEVATION_BATCH]
        locations = "|".join(f"{java_double(lat)},{java_double(lon)}" for lat, lon in batch)
        data = get_json(f"{base}/v1/srtm30m?locations={urllib.parse.quote(locations, safe=',|')}")
        if data.get("status") != "OK" or len(data.get("results", [])) != len(batch):
            raise RuntimeError("serviço de elevação respondeu com erro")
        for point, result in zip(batch, data["results"]):
            if result.get("elevation") is not None:
                found[point] = result["elevation"]
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", required=True, help="JSON: [{id, latitude, longitude}, ...]")
    parser.add_argument("--osrm", default="http://osrm:5000")
    parser.add_argument("--elevation", default="http://elevation:5000")
    args = parser.parse_args()
    points = json.loads(open(args.points, encoding="utf-8").read()) if args.points != "-" else json.load(sys.stdin)

    traced = []
    for a in points:
        for b in points:
            if a["id"] != b["id"]:
                start, end = (a["latitude"], a["longitude"]), (b["latitude"], b["longitude"])
                distance, duration, geometry = osrm_route(args.osrm, start, end)
                traced.append((a["id"], b["id"], distance, duration, resample(geometry, SAMPLE_STEP_METERS)))
    heights = elevations(args.elevation, [snapped(s) for item in traced for s in item[4]])

    pairs = []
    for origin, destination, distance, duration, samples in traced:
        speed = FALLBACK_SPEED_KMH if duration <= 0 else max(MIN_SPEED_KMH, min(MAX_SPEED_KMH, distance / duration * 3.6))
        profile = [heights.get(snapped(s)) for s in samples]
        pairs.append({
            "from_point": origin, "to_point": destination,
            "distance_meters": distance, "duration_seconds": duration,
            "average_speed_kmh": speed, "slope_percent": slope_percent(profile, distance),
            "samples": len(samples),
        })
    json.dump(pairs, sys.stdout)


if __name__ == "__main__":
    main()
