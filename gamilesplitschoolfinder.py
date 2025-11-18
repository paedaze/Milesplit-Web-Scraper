import sqlite3
from scrapy import Request
from scrapy import crawler
from scrapy import spiders
from scrapy.crawler import CrawlerProcess

# Web spider for scraping all ga milesplit schools (school names and roster links)
class gamilesplit_school_scraper(spiders.Spider):
    name = 'schools'
    start_urls = ["https://ga.milesplit.com/teams"]

    def __init__(self, school_links, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.school_links = school_links
    
    def parse(self, response):
        table = response.xpath("//table[@class='teams order-table table']/tbody/tr/td/a")
        for school in table:
            school_name = school.xpath("text()").get(default="").strip()
            if "null" in school_name or 'Brookwood High School' == school_name:
                continue
            else:
                self.school_links[school_name] = school.attrib["href"] + '/roster'

# Function used to run the ga school milesplit data scraper and add the scraped data to the database
def update_school_database():
    # Connect to a database (or create a new one if it doesn't exist)
    conn = sqlite3.connect('ga-milesplit-school-database.db')
    cursor = conn.cursor()

    # Create a table
    cursor.execute("CREATE TABLE IF NOT EXISTS gamilesplitschools (name TEXT, link TEXT)")

    # Run web spider
    school_links = {}
    process = CrawlerProcess()
    process.crawl(gamilesplit_school_scraper, school_links=school_links)
    process.start()

    # Insert data into database
    for school_name, school_link in school_links.items():
        cursor.execute("INSERT INTO gamilesplitschools (name, link) VALUES (?, ?)", (school_name, school_link))

    conn.commit()
    conn.close()

# FOR DEVELOPER USAGE: Used to read the database
def read_school_database():
    # Connect to a database (or create a new one if it doesn't exist)
    conn = sqlite3.connect('ga-milesplit-school-database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name, link FROM gamilesplitschools")

    schools = cursor.fetchall()
    for row in schools:
        print(row)


if __name__ == '__main__':
    response = input(str('Do you want to update or read? (U/R): '))
    if response.upper() == 'U':
        update_school_database()
    elif response.upper() == 'R':
        read_school_database()
    
        
