from scrapy.crawler import CrawlerProcess
import scraper
from scraper import athlete_spider
from scraper import html_paths
from scraper import Sport
from flask import Flask, render_template

# Function to convert string to enum
def string_to_enum(Enum, string):
    for enum in Enum:
        if enum.name == string:
            return enum
    raise ValueError(f"'{string}' is not a valid enum name")



