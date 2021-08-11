import scrapy
from urllib.parse import urlparse
from html_text import extract_text
from scrapy.shell import inspect_response

class FacultySpider(scrapy.Spider):
    # command: scrapy crawl faculty -O data/facultymain.py

    name = 'faculty'
    # allowed_domains = ['https://www.cs.washington.edu/']
    start_urls = ['https://www.cs.washington.edu/people/faculty/']

    def parse(self, response):
        facultyrows = response.css("div.row.directory-row")
        for row in facultyrows:
            # initailize empty dict to pass to meta arg of scrapy.Request
            meta = {}
            # get every child row with data on professor
            rowdivs = row.css("div.col-sm-10").xpath('.//div')
            for div in rowdivs:
                key = div.xpath("@class").get()
                value = extract_text(div.get())
                meta[key] = value
            meta["faculty_homepage"] = row.css("div.directory-name").css("a::attr(href)").get()
            yield meta
