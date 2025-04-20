from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from scrapy import spiders
from scrapy.crawler import CrawlerProcess
from enum import Enum
from terminaltables3 import AsciiTable

class Sport(Enum):
    CROSS_COUNTRY = 3
    OUTDOOR_TRACK = 2
    INDOOR_TRACK = 1

class Event(Enum):
    FIVE_THOUSAND = '5000 Meter Run'
    THIRTYTWO_HUNDRED = '3200 Meter Run'
    SIXTEEN_HUNDRED = '1600 Meter Run'
    EIGHT_HUNDRED = '800 Meter Run'
    FOUR_HUNDRED = '400 Meter Run'
    TWO_HUNDRED = '200 Meter Run'
    ONE_HUNDRED = '100 Meter Run'

html_paths = {
    'options_id' : 'postHeaderSearchCategory',
    'search_school_id' : 'postHeaderSearch',
    'search_button_class' : 'input-group-append',
    'sport_dropdown_id' : 'rosterFilterType',
    'roster_parent_xpath' : "//ul[@id='rosterDataset']",
    'student_info_xpath' : "div[@class='data-point w-30 w-md-50 d-flex align-items-center']/a",
    'student_record_table_xpath' : "//div[@class='record-box']/table/tbody",
    'student_event_time' : "//td[@class='event']",
}

# Set up milesplit settings
# Geniunally fuck this dum ahh language python ts does not deserve any of its love it gets i was trying to debug ts for TWEO FUCKLDNI  HORUS and i found that the problem with ts is that oop is fujcking doghist in python and evveryhting is so abstrac and shitty its imposibble to rpgorma anyhtirng cool fdvaodfsjnvairofvnao;eruvwena;irjuesrivwenprtvjsdnfkvjbsnf
school_link = []
athlete_infos = {}
athlete_race_infos = []
event = []

# Function to get the school page link from the search results
def get_school_link(driver, school_name):
    # Accesses the search page of the website
    driver.get("https://ga.milesplit.com/search")

    # Selects the Teams option from the dropdown menu
    dropdown = Select(driver.find_element(By.ID, html_paths['options_id']))
    dropdown.select_by_value('team')

    # Finds and selects the school 
    txtBox = driver.find_element(By.ID, html_paths['search_school_id'])
    txtBox.send_keys(school_name)

    # Submit the search form (clicks the 'search' button)
    driver.find_element(By.CLASS_NAME, html_paths['search_button_class']).find_element(By.TAG_NAME, 'button').click()

    # Find the link to the team page via the first search result (Waits for the search results to load, timeout given in the WebDriverWait parameter)
    wait = WebDriverWait(driver, 10)
    try:
        school_link = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'result-description')))[0].get_attribute('href')
    except:
        driver.quit()
        print("No results found")
        return None

    driver.quit()
    return school_link + '/roster' # Returns the school roster link

# Web spider for handling athlete data scraping
# This spider scrapes the athlete data from the school page and stores it in a dictionary in main.py
class athlete_spider(spiders.Spider):
    name = 'athletes'
    start_urls = school_link

    def parse(self, response): # Parse the school roster page
        athlete_active_seasons = response.xpath(html_paths['roster_parent_xpath']).xpath(html_paths['data_season_id']) # gets the athlets of the chosen sport
        for season in athlete_active_seasons:
            athlete_row = season.xpath('..')
            athlete_name = athlete_row.xpath(html_paths['student_info_xpath'] + "/text()").get()
            athlete_link = athlete_row.xpath(html_paths['student_info_xpath']).attrib["href"]
            athlete_infos[athlete_link] = athlete_name

            yield response.follow(athlete_link, self.parse_athlete_info) # follow the link to the athlete page
    
    def parse_athlete_info(self, response): # Parse each athlete's page
        table = response.xpath(html_paths['student_event_time']).xpath('..') # table containing info on each event and event time
        athlete_name = athlete_infos[response.url]

        for row in table:
            event_name = row.xpath("td[@class='event']/text()").get()
            event_time = row.xpath("td[@class='time']/text()").get()

            if event_name == event[0].value: # event found through iteration == event set in main.py
                yield {
                    'name': athlete_name,
                    'event': event_name,
                    'time': event_time
                }
                athlete_race_infos.append([athlete_name, event_name, event_time])
                break

# Function to convert string to enum
def string_to_enum(Enum, string):
    for enum in Enum:
        if enum.name == string:
            return enum
    raise ValueError(f"'{string}' is not a valid enum name")

def main():
    # Set the school given by user input
    school_name = input("Enter the school name: ")
    print("Searching for {}...".format(school_name))

    # Set up the driver
    op = webdriver.ChromeOptions()
    op.add_argument("--headless=new")
    driver = webdriver.Chrome(options=op)
    # Search for school
    school_link.append(get_school_link(driver, school_name))

    # Set the sport given by user input
    sport = string_to_enum(Sport, input("Enter the sport (cross_country, outdoor_track, indoor_track): ").upper())
    html_paths['data_season_id'] = "//li[@class='athlete-row data-row']/div[@data-season-id='{}']".format(sport.value)

    # Set the event given by user input
    event_input = input("Enter the event (5000, 3200, 1600, 800, 400, 200, 100): ") + ' Meter Run'
    event.append(Event(event_input))

    # Run web spiders
    process = CrawlerProcess()
    process.crawl(athlete_spider)
    process.start()

    athlete_race_infos.insert(0, ['Athlete', 'Event', 'Time']) # Add header to the table
    table = AsciiTable(athlete_race_infos)
    print(table.table)

main()

