from pathlib import Path
import sqlite3

from flask import Flask, jsonify, render_template
from scrapy.crawler import CrawlerProcess

import scraper
from scraper import Sport, athlete_spider, html_paths


# Function to convert string to enum
def string_to_enum(Enum, string):
    for enum in Enum:
        if enum.name == string:
            return enum
    raise ValueError(f"'{string}' is not a valid enum name")


app = Flask(__name__)
DATABASE_PATH = Path(__file__).resolve().parent / "ga-milesplit-school-database.db"


def load_school_map():
    """Read the GA Milesplit school data from the SQLite database."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, link FROM gamilesplitschools ORDER BY name")
        schools = cursor.fetchall()
    return {name: link for name, link in schools}


@app.route("/")
def index():
    name = 'Aaron'
    return render_template("index.html", name=name)


@app.route("/api/schools")
def schools():
    return jsonify(load_school_map())


if __name__ == '__main__':
    app.run(debug=True)
