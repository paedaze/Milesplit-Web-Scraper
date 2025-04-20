from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from scrapy import spiders
from enum import Enum

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
    'student_name_xpath' : "//h1[@class='athlete-name']/text()"
}

# Function to dynamically get the school page link from the search results
def get_school_link(school_name):
    # Set up the driver
    op = webdriver.ChromeOptions()
    op.add_argument("--headless=new")
    driver = webdriver.Chrome(options=op)
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
        link = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'result-description')))[0].get_attribute('href')
    except:
        driver.quit()
        print("No results found")
        return None

    driver.quit()
    return link + '/roster' # Returns the school roster link

# Web spider for handling athlete data scraping
# This spider scrapes the athlete data from the school page and stores it in a dictionary in main.py
class athlete_spider(spiders.Spider):
    name = 'athletes'

    def __init__(self, school_link, sport, event, athlete_info_output, *args, **kwargs): # Allow spider to access school link and event
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