from scrapy.crawler import CrawlerProcess
from scraper import athlete_spider
from scraper import get_school_link
from scraper import html_paths
from scraper import Sport
from scraper import Event
from terminaltables3 import AsciiTable

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

    # Search for school
    school_link = get_school_link(school_name)

    # Set the sport given by user input
    sport = string_to_enum(Sport, input("Enter the sport (cross_country, outdoor_track, indoor_track): ").upper())
    html_paths['data_season_id'] = "//li[@class='athlete-row data-row']/div[@data-season-id='{}']".format(sport.value)

    # Set the event given by user input
    event_input = input("Enter the event (5000, 3200, 1600, 800, 400, 200, 100): ") + ' Meter Run'
    event = Event(event_input)

    athlete_info_output = []

    # Run web spiders
    process = CrawlerProcess()
    process.crawl(athlete_spider, school_link=school_link, sport=sport, event=event, athlete_info_output=athlete_info_output)
    process.start()

    athlete_table = ['Name', 'Event', 'Time'] + athlete_info_output
    table = AsciiTable(athlete_table)
    print(table.table)

main()
