from pathlib import Path
from collections import defaultdict
import sqlite3
from math import inf

from flask import Flask, jsonify, render_template, request

from scraper import Event, Gender, Sport


# Function to convert string to enum
def string_to_enum(Enum, string):
    for enum in Enum:
        if enum.name == string:
            return enum
    raise ValueError(f"'{string}' is not a valid enum name")


app = Flask(__name__)
DATABASE_PATH = Path(__file__).resolve().parent / "ga-milesplit-school-database.db"
ATHLETES_DATABASE_PATH = Path(__file__).resolve().parent / "athletes.db"
TRACK_POINTS = (10, 8, 6, 5, 4, 3, 2, 1)


def load_school_map():
    """Read the GA Milesplit school data from the SQLite database."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, link FROM gamilesplitschools ORDER BY name")
        schools = cursor.fetchall()
    return {name: link for name, link in schools}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/schools")
def schools():
    return jsonify(load_school_map())


def time_to_seconds(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    cleaned = "".join(ch for ch in value if ch.isdigit() or ch in {":", "."})
    if not cleaned:
        return None
    parts = cleaned.split(":")
    try:
        total = 0.0
        for part in parts:
            if not part:
                return None
            total = total * 60 + float(part)
        return total
    except ValueError:
        return None


def fetch_finishers(selected_schools, event: Event, gender: Gender):
    if not selected_schools:
        return [], selected_schools
    placeholders = ",".join("?" for _ in selected_schools)
    query = f"""
        SELECT a.name AS athlete_name,
               s.school_name AS school_name,
               r.time AS performance
        FROM results r
        JOIN athletes a ON r.athlete_id = a.athlete_id
        JOIN events e ON r.event_id = e.event_id
        JOIN schools s ON r.school_id = s.school_id
        JOIN genders g ON r.gender_id = g.gender_id
        WHERE e.event_name = ?
          AND g.gender = ?
          AND s.school_name IN ({placeholders})
    """
    params = [event.value, gender.value, *selected_schools]
    with sqlite3.connect(ATHLETES_DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        seconds = time_to_seconds(row["performance"])
        if seconds is None:
            continue
        grouped[row["school_name"]].append(
            {
                "athlete": row["athlete_name"],
                "school": row["school_name"],
                "time": row["performance"],
                "seconds": seconds,
            }
        )
    finishers = []
    for athletes in grouped.values():
        athletes.sort(key=lambda entry: entry["seconds"])
        finishers.extend(athletes[:7])
    finishers.sort(key=lambda entry: entry["seconds"])
    missing = sorted({school for school in selected_schools if school not in grouped})
    return finishers, missing


def calculate_points(sport: Sport, place: int) -> int:
    if sport in (Sport.INDOOR_TRACK, Sport.OUTDOOR_TRACK):
        if 0 < place <= len(TRACK_POINTS):
            return TRACK_POINTS[place - 1]
        return 0
    if sport == Sport.CROSS_COUNTRY:
        return place
    return 0


def build_athlete_rows(entries, sport: Sport):
    rows = []
    for index, entry in enumerate(entries, start=1):
        rows.append(
            {
                "place": index,
                "athlete": entry["athlete"],
                "school": entry["school"],
                "time": entry["time"],
                "points": calculate_points(sport, index),
            }
        )
    return rows


def score_cross_country(entries):
    team_positions = defaultdict(list)
    for index, entry in enumerate(entries, start=1):
        team_positions[entry["school"]].append(index)
    results = []
    for school, places in team_positions.items():
        result = {
            "school": school,
            "finisher_count": len(places),
            "places": places[:7],
            "eligible": len(places) >= 5,
            "score": None,
            "sixth_runner": None,
            "top_four_total": None,
            "status": "",
            "tiebreak_note": "",
        }
        if result["eligible"]:
            result["score"] = sum(places[:5])
            result["sixth_runner"] = places[5] if len(places) >= 6 else None
            result["top_four_total"] = sum(places[:4])
            result["status"] = "Scored"
        else:
            result["status"] = "Forfeit (needs 5 finishers)"
        results.append(result)

    def sort_key(item):
        if not item["eligible"]:
            return (inf, inf, inf, item["school"])
        sixth = item["sixth_runner"] if item["sixth_runner"] is not None else inf
        top_four = item["top_four_total"] if item["top_four_total"] is not None else inf
        return (item["score"], sixth, top_four, item["school"])

    results.sort(key=sort_key)
    eligible_groups = defaultdict(list)
    for item in results:
        if item["eligible"] and item["score"] is not None:
            eligible_groups[item["score"]].append(item)

    for group in eligible_groups.values():
        if len(group) <= 1:
            continue
        sixth_values = [g["sixth_runner"] if g["sixth_runner"] is not None else inf for g in group]
        if len(set(sixth_values)) > 1:
            best = min(sixth_values)
            for team, value in zip(group, sixth_values):
                note = "Won tie via 6th runner" if value == best else "Lost tie via 6th runner"
                team["tiebreak_note"] = note
            continue
        top_four_values = [g["top_four_total"] for g in group]
        if len(set(top_four_values)) > 1:
            best = min(top_four_values)
            for team, value in zip(group, top_four_values):
                note = "Won tie via top 4 runners" if value == best else "Lost tie via top 4 runners"
                team["tiebreak_note"] = note
        else:
            for team in group:
                team["tiebreak_note"] = "Tie remains after tiebreakers"
    return results


@app.route("/api/simulate", methods=["POST"])
def simulate_meet():
    payload = request.get_json(silent=True) or {}
    raw_schools = payload.get("schools") or []
    if not isinstance(raw_schools, list):
        return jsonify({"error": "Schools must be a list."}), 400
    schools = [name for name in (str(item).strip() for item in raw_schools) if name]
    schools = list(dict.fromkeys(schools))
    sport_name = payload.get("sport")
    event_name = payload.get("event")
    gender_name = payload.get("gender")
    if not schools or not sport_name or not event_name or not gender_name:
        return jsonify({"error": "Schools, sport, event, and gender are required."}), 400
    try:
        sport = string_to_enum(Sport, sport_name)
        event = string_to_enum(Event, event_name)
        gender = string_to_enum(Gender, gender_name)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    finishers, missing = fetch_finishers(schools, event, gender)
    athlete_rows = build_athlete_rows(finishers, sport)
    message = ""
    if not finishers:
        message = "No athletes match the selected filters."
    team_scores = score_cross_country(finishers) if sport == Sport.CROSS_COUNTRY else []
    return jsonify(
        {
            "athletes": athlete_rows,
            "team_scores": team_scores,
            "sport": sport.name,
            "finishers": len(finishers),
            "missing_schools": missing,
            "message": message,
        }
    )


if __name__ == '__main__':
    app.run(debug=True)
