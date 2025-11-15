from scrapy import spiders
from scrapy.crawler import CrawlerProcess

from enum import Enum

import sqlite3

class Sport(Enum):
    CROSS_COUNTRY = 3
    OUTDOOR_TRACK = 2
    INDOOR_TRACK = 1

class Event(Enum):
    FIVE_THOUSAND = '5000 Meter Run'
    TWO_MILE = '2 Mile Run'
    THIRTYTWO_HUNDRED = '3200 Meter Run'
    SIXTEEN_HUNDRED = '1600 Meter Run'
    FIFTEEN_HUNDRED = '1500 Meter Run'
    TWELVE_HUNDRED = '1200 Meter Run'
    EIGHT_HUNDRED = '800 Meter Run'
    FOUR_HUNDRED = '400 Meter Dash'
    TWO_HUNDRED = '200 Meter Dash'
    ONE_HUNDRED = '100 Meter Dash'

class Gender(Enum):
    MALE = 'm'
    FEMALE = 'f'

EVENT_VALUES = {event.value for event in Event}

HTML_PATHS = {
    'roster_parent_xpath': "//ul[@id='rosterDataset']",
    'student_info_xpath': "div[@class='data-point w-30 w-md-50 d-flex align-items-center']/a",
    'student_gender_xpath': "div[@class='data-point w-20 w-md-10 text-lighter text-center text-uppercase column-gender']",
    'student_event_time_from_heading': "following-sibling::table[1]//tr[td[@class='event']]",
    'student_name_xpath': "//h1[@class='athlete-name']/text()"
}

def initialize_database():
    # Connect to a database (or create a new one if it doesn't exist)
    conn = sqlite3.connect('athletes.db')
    cursor = conn.cursor()

    # Create tables for athletes, events, schools, and results: normalized strategy for data
    cursor.execute("CREATE TABLE IF NOT EXISTS athletes (athlete_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS events (event_id INTEGER PRIMARY KEY AUTOINCREMENT, event_name TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS genders (gender_id INTEGER PRIMARY KEY AUTOINCREMENT, gender_name TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS schools (school_id INTEGER PRIMARY KEY AUTOINCREMENT, school_name TEXT UNIQUE NOT NULL)")
    cursor.execute(
    '''
        CREATE TABLE IF NOT EXISTS results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            school_id INTEGER NOT NULL,
            gender_id INTEGER NOT NULL,
            time TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes (athlete_id),
            FOREIGN KEY (event_id) REFERENCES events (event_id),
            FOREIGN KEY (school_id) REFERENCES schools (school_id),
            FOREIGN KEY (gender_id) REFERENCES genders (gender_id),
            UNIQUE (athlete_id, event_id)
        )
    '''
    )

    # Populate table for events
    for event in Event:
        cursor.execute("INSERT OR IGNORE INTO events (event_name) VALUES (?)", (event.value,))

    # Populate table for genders
    for gender in Gender:
        cursor.execute("INSERT OR IGNORE INTO genders (gender_name) VALUES (?)", (gender.value,))

    # Populate table for schools
    with sqlite3.connect('ga-milesplit-school-database.db') as school_conn:
        school_db_cursor = school_conn.cursor()
        school_db_cursor.execute("SELECT name FROM gamilesplitschools ORDER BY name")
        rows = school_db_cursor.fetchall()
    for row in rows:
        cursor.execute("INSERT OR IGNORE INTO schools (school_name) VALUES (?)", (row))

    conn.commit()
    conn.close()

# FOR DEVELOPER TESTING: Prints out the athletes.db database to the terminal
def read_database():
    conn = sqlite3.connect('athletes.db')
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT a.name, e.event_name, r.time
        FROM athletes a
        LEFT JOIN results r ON a.athlete_id = r.athlete_id
        LEFT JOIN events e ON r.event_id = e.event_id
        ORDER BY a.name, e.event_name
        """
    )
    rows = cursor.fetchall()
    if not rows:
        print("No athlete data found in athletes.db")
    else:
        current_name = None
        has_events = False
        for name, event_name, event_time in rows:
            if name != current_name:
                if current_name is not None and not has_events:
                    print("  No recorded events.")
                print(f"Athlete: {name}")
                current_name = name
                has_events = False
            if event_name:
                display_time = event_time if event_time else "N/A"
                print(f"  {event_name}: {display_time}")
                has_events = True
        if current_name is not None and not has_events:
            print("  No recorded events.")
        conn.close()

# Web spider for handling athlete data scraping
# This spider scrapes the athlete data from the school page and stores it in 'athlete_info_output'
class athlete_spider(spiders.Spider):
    name = 'athletes'

    def __init__(self, school_link, sport, *args, **kwargs): # Allow spider to access school link, sport, event, and the output
        super().__init__(*args, **kwargs)
        self.school_link = school_link
        self.sport = sport
        self.start_urls = [self.school_link]
        self.school_name = ''
        initialize_database()

    def parse(self, response): # Parse the school roster page
        self.school_name = response.xpath("//section[@class='jumbotron-content']/h1/text()").get()
        data_season_xpath = "//li[@class='athlete-row data-row']/div[@data-season-id='{}']".format(self.sport.value) # Set the xpath for the sport
        athlete_active_seasons = response.xpath(HTML_PATHS['roster_parent_xpath']).xpath(data_season_xpath) # Gets the athletes of the chosen sport
        for season in athlete_active_seasons: # Iterates over all athletes of the given sport
            athlete_row = season.xpath('..')
            athlete_link = athlete_row.xpath(HTML_PATHS['student_info_xpath']).attrib["href"]
            gender = Gender(athlete_row.xpath(HTML_PATHS['student_gender_xpath'] + '/text()').get())
            
            yield response.follow(athlete_link, self.parse_athlete_info, cb_kwargs=dict(gender=gender)) # follow the link to the athlete page
    
    def parse_athlete_info(self, response, gender): # Parse each athlete's page
        # Find athlete name
        athlete_name = response.xpath(HTML_PATHS['student_name_xpath']).get()

        # Initialize database connection
        conn = sqlite3.connect('athletes.db')
        cursor = conn.cursor()

        # Insert athlete entry and Find athlete_id from athlete_name
        cursor.execute("INSERT OR IGNORE INTO athletes (name) VALUES (?)", (athlete_name,))
        cursor.execute("SELECT athlete_id FROM athletes WHERE name = ?", (athlete_name,))
        athlete_row = cursor.fetchone()
        if not athlete_row:
            return 
        athlete_id = athlete_row[0]

        # Find school_id from school_name
        cursor.execute("SELECT school_id FROM schools WHERE school_name = ?", (self.school_name,))
        school_row = cursor.fetchone()
        if not school_row:
            return
        school_id = school_row[0]

        # Find gender_id from gender
        cursor.execute("SELECT gender_id FROM genders WHERE gender_name = ?", (gender.value,))
        gender_row = cursor.fetchone()
        if not gender_row:
            return
        gender_id = gender_row[0]

        # Find high school record box
        high_school_heading = None
        for heading in response.xpath("//h5[@class='box-heading']"):
            heading_text = heading.xpath("normalize-space()").get() or ""
            if "High School" in heading_text:
                high_school_heading = heading
                break
        if not high_school_heading:
            return
        table = high_school_heading.xpath(HTML_PATHS['student_event_time_from_heading']) # High school record table
    
        # Iterate through the table of track/xc events from the high school record box found previously
        for row in table:
            event_name = row.xpath("td[@class='event']/text()").get()
            event_time = row.xpath("td[@class='time']/text()").get()

            if event_name not in EVENT_VALUES:
                print(event_name + " not included in Event Enum")
                continue

            # Find event_id through event_name
            cursor.execute("SELECT event_id FROM events WHERE event_name = ?", (event_name,))
            event_row = cursor.fetchone()
            if not event_row:
                continue
            event_id = event_row[0]

            cursor.execute("INSERT OR REPLACE INTO results (athlete_id, event_id, school_id, gender_id, time) VALUES (?, ?, ?, ?, ?)", (athlete_id, event_id, school_id, gender_id, event_time))
        
        conn.commit()
        conn.close()

def main():
    inp = input(str('Do you want to scrape data, read data, or initialize database? (S/R/I): '))
    if inp.upper() == 'S':
        process = CrawlerProcess()
        process.crawl(athlete_spider, school_link='https://ga.milesplit.com/teams/4452-parkview-high-school/roster', sport=Sport.CROSS_COUNTRY)
        process.start()
    elif inp.upper() == 'R':
        read_database()
    elif inp.upper() == 'I':
        initialize_database()

if __name__ == '__main__':
    main()
