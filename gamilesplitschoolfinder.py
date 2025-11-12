import pprint
from scrapy import Request
from scrapy import crawler
from scrapy import spiders
from scrapy.crawler import CrawlerProcess


def dict_to_instantiable_string(dictionary):
    # Return a copy/paste-ready assignment that recreates the provided dictionary
    literal = pprint.pformat(dictionary, sort_dicts=True, width=100)
    return f"copied_dict = {literal}"

class get_ga_school_links(spiders.Spider):
    name = 'schools'
    start_urls = ["https://ga.milesplit.com/teams"]

    def __init__(self, school_links, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.school_links = school_links
    
    def parse(self, response):
        table = response.xpath("//table[@class='teams order-table table']/tbody/tr/td/a")
        for school in table:
            school_name = school.xpath("text()").get(default="").strip()
            if "null" not in school_name:
                school_links[school_name] = school.attrib["href"]


if __name__ == "__main__":
    school_links = {}
    process = CrawlerProcess()
    process.crawl(get_ga_school_links, school_links=school_links)
    process.start()
    print(dict_to_instantiable_string(school_links))