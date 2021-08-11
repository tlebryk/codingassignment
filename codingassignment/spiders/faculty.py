import scrapy
from urllib.parse import urlparse
from html_text import extract_text
from scrapy.shell import inspect_response

class FacultySpider(scrapy.Spider):
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


    def facultyparse(self, response):
        # can move this up into parse to send to proper parsing function? and never actually fetch...?
        if urlparse(response.url).netloc == "https://www.cs.washington.edu/":
            menunav = response.css("ul.menu")
            # first menu nav is main nav bar, we care about second nav bar links
            pages = menunav[1].css("a")
            for page in pages:
                url = page.css("::attr(href)").get()
                name = extract_text(page.get())
                # data = 

            pass
        else:
            pass
            # save name of faculty member to parse by hand

    def subpageparse(self, response):
        """
        faculty pages have subpages like 'Biography', 'Research', 
        'Publications', 'Presentations'
        """
        pass