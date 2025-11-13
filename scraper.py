from scrapy import spiders
from enum import Enum

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
    FOUR_HUNDRED = '400 Meter Run'
    TWO_HUNDRED = '200 Meter Run'
    ONE_HUNDRED = '100 Meter Run'

html_paths = {
    'roster_parent_xpath' : "//ul[@id='rosterDataset']",
    'student_info_xpath' : "div[@class='data-point w-30 w-md-50 d-flex align-items-center']/a",
    'student_event_time' : "//td[@class='event']",
    'student_name_xpath' : "//h1[@class='athlete-name']/text()"
}

# Web spider for handling athlete data scraping
# This spider scrapes the athlete data from the school page and stores it in 'athlete_info_output'
class athlete_spider(spiders.Spider):
    name = 'athletes'

    def __init__(self, school_link, sport, event, athlete_info_output, *args, **kwargs): # Allow spider to access school link, sport, event, and the output
        super().__init__(*args, **kwargs)
        self.school_link = school_link
        self.sport = sport
        self.event = event
        self.athlete_info_output = athlete_info_output
        self.start_urls = [self.school_link]

    def parse(self, response): # Parse the school roster page
        html_paths['data_season_id'] = "//li[@class='athlete-row data-row']/div[@data-season-id='{}']".format(self.sport.value) # Set the xpath for the sport
        athlete_active_seasons = response.xpath(html_paths['roster_parent_xpath']).xpath(html_paths['data_season_id']) # Gets the athletes of the chosen sport
        for season in athlete_active_seasons:
            athlete_row = season.xpath('..')
            athlete_link = athlete_row.xpath(html_paths['student_info_xpath']).attrib["href"]

            yield response.follow(athlete_link, self.parse_athlete_info) # follow the link to the athlete page
    
    def parse_athlete_info(self, response): # Parse each athlete's page
        table = response.xpath(html_paths['student_event_time']).xpath('..') # table containing info on each event and event time
        athlete_name = response.xpath(html_paths['student_name_xpath']).get()

        for row in table:
            event_name = row.xpath("td[@class='event']/text()").get()
            event_time = row.xpath("td[@class='time']/text()").get()

            if event_name == self.event.value: # event found through iteration == event set in main.py
                yield {
                    'name': athlete_name,
                    'event': event_name,
                    'time': event_time
                }
                self.athlete_info_output.append([athlete_name, event_name, event_time])
                break
