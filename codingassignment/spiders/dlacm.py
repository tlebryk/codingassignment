import scrapy
from urllib.parse import urlparse
from html_text import extract_text
import pandas as pd
import os
from datetime import datetime
import re
from dateutil import parser
import logging
from fuzzywuzzy import process
from scrapy.utils.log import configure_logging
from scrapy.shell import inspect_response

DATETIMENOW = datetime.now().strftime("%Y%m%d_%H%M%S")
HOMEDIR = os.path.expanduser("~")

logger = logging.RootLogger(1)
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename=f"C:/Users/tlebr/Google Drive/Personal/codingassignment/logs/dlacm_{DATETIMENOW}.log",
    level=logging.INFO,
)


class DlAcmSearchSpider(scrapy.Spider):
    # command: scrapy crawl dlacmsearch -O data/dlacmseearch.py
    # create/update a single a master linkedin csv with info about each person
    # create a professional history csv for each perosn
    name = "dlacmsearch"

    def __init__(self, **kwargs):
        configure_logging(install_root_handler=False)
        self.df = pd.read_csv(
            r"C:/Users/tlebr/Google Drive/Personal/codingassignment/data/facultymain.csv",
            encoding="unicode_escape",
        )
        numpgs = 8  # hardcoded value for uw
        self.start_urls = [
            f"https://dl.acm.org/people?ContribAffiliationId=10.1145%2Finstitution-60015481&startPage={i}&pageSize=50"
            for i in range(numpgs)
        ]
        super().__init__(**kwargs)

    def parse(self, response):
        # inspect_response(response, self)
        ppl = response.css("li.col-md-6.col-lg-4.people__people-list")
        for p in ppl:
            data = {}
            name = extract_text(p.css("div.name").get())
            match = process.extractOne(name, self.df.name)
            data["dlacm_name"] = name
            data["bestmatchscore"] = match[1]
            data["name"] = match[0]
            df2 = pd.DataFrame(data, index=[0]).merge(self.df, on="name", how="left")
            data = df2.to_dict(orient="list")
            for key, value in data.items():
                data[key] = value[0]
            data["dlcam_profile"] = response.urljoin(
                p.css("a.view-profile::attr(href)").get()
            )
            data["dlacm_location"] = extract_text(p.css("div.location").get())
            links = p.css("a.btn--icon")
            for link in links:
                key = f"dlcam_{link.xpath('@data-title').get()}".replace(
                    " ", "_"
                ).lower()
                value = link.xpath("@href").get()
                if not data.get(key):
                    data[key] = value
            data["dlcam_email"] = extract_text(
                p.xpath(".//a[contains(@data-title, 'Author’s Email')]").get()
            )
            data["dlcam_website"] = extract_text(
                p.xpath(".//a[contains(@data-title, 'Author’s Website')]").get()
            )
            logging.info(data)
            yield data


class DlAcmInstitutionSpider(scrapy.Spider):
    # command: scrapy crawl dlacminst -O data/dlacminstitution.py
    # search all people from uw's institution page
    # ranks how well the name matches; as general rule match > 90 is pretty reliable.
    name = "dlacminst"

    def __init__(self, **kwargs):
        configure_logging(install_root_handler=False)
        self.logging = logging
        self.logging.basicConfig(
            format="%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            filename=f"C:/Users/tlebr/Google Drive/Personal/codingassignment/logs/dlacminstspider_{DATETIMENOW}.log",
            level=logging.INFO,
        )
        self.df = pd.read_csv(
            r"C:/Users/tlebr/Google Drive/Personal/codingassignment/data/facultymain.csv",
            encoding="unicode_escape",
        )
        self.start_urls = [
            f"https://dl.acm.org/institution/60015481/authors?pageSize=50&startPage={i}&sortBy=ContribSurnameSortField"
            for i in range(108)  # change to 108 later
        ]
        # super().__init__(**kwargs)

    def parse(self, response):
        # inspect_response(response, self)
        ppl = response.css("li.search__item.card--shadow.contrib-list__list")
        for p in ppl:
            data = {}
            data["dlacm_insturl"] = response.url
            data["dlacm_profile"] = response.urljoin(
                p.css("a.contrib-link::attr(href)").get()
            )
            name = extract_text(p.css("span.list__title").get())
            match = process.extractOne(name, self.df.name)
            data["dlacm_name"] = name
            data["name"] = match[0]
            data["bestmatchscore"] = match[1]
            df2 = pd.DataFrame(data, index=[0]).merge(self.df, on="name", how="left")
            data = df2.to_dict(orient="list")
            for key, value in data.items():
                data[key] = value[0]
            citations = p.css("div.list__count.hidden-xs")
            data["dlacm_citations"] = extract_text(citations.get())
            data["dlacm_citations_link"] = extract_text(
                citations.css("a::attr(href)").get()
            )
            self.logging.info(data)
            # logger.info(data)
            yield data


class DlAcmProfileSpider(scrapy.Spider):
    # command: scrapy crawl dlacmprof -O data/dlcmprofiles.py

    # cycle through all the profiles found from DlAcmInstitutionSpider
    # fuzzy match on names; match > 90 is pretty reliable.
    name = "dlacmprof"
    custom_settings = {
        "LOG_FILE": f"C:/Users/tlebr/Google Drive/Personal/codingassignment/logs/dlacmprofspider_{DATETIMENOW}.log"
    }
    # allowed_domains = "dl.acm.org"

    def __init__(self, **kwargs):
        configure_logging(install_root_handler=False)
        self.df = pd.read_csv(
            r"C:/Users/tlebr/Google Drive/Personal/codingassignment/data/dlacminstitution90.csv",
            encoding="unicode_escape",
        )

    def start_requests(self):
        # if multiple profiles with same name, group together
        for name, group in self.df.groupby("name"):  # TODO: remove []:1]
            for url in group.dlacm_profile:
                url2 = (
                    url
                    + "/publications?Role=author&pageSize=20&startPage={}&sortBy=Ppub_desc"  # TODO: change back to 50
                )
                meta = {"name": name, "id": group.id.iloc[0]}
                logging.info(meta)
                cb_kwargs = {"baseurl": url2, "pg": 0}
                yield scrapy.Request(
                    url2.format(0), callback=self.parse, meta=meta, cb_kwargs=cb_kwargs
                )

    def parse(self, response, baseurl, pg):
        logging.info("parsing...")
        # inspect_response(response, self)
        articles = response.css("li.search__item.issue-item-container")
        for article in articles:
            data = {}
            data["name"] = response.meta["name"]
            data["facultyid"] = int(response.meta["id"])
            title = article.css("h5.issue-item__title")
            data["title"] = extract_text(title.get())
            data["arturl"] = response.urljoin(title.xpath(".//a/@href").get())
            data["type_pub"] = extract_text(response.css("div.issue-heading").get())
            data["abstract"] = extract_text(
                article.css("div.issue-item__abstract").get()
            )
            data["journal_name"] = extract_text(
                article.css("span.epub-section__title").get()
            )
            data["publication_date"] = extract_text(
                response.css("span.dot-separator").css("span").get()
            ).split(",")[0]
            try:
                data["publication_year"] = int(
                    parser.parse(data["publication_date"]).year
                )
            except:
                data["publication_year"] = None
            data["citations"] = extract_text(
                response.css("span.citation").css("span").get()
            )
            data["downloads"] = extract_text(
                response.css("span.metric").css("span").get()
            )
            authors = article.css("ul.rlist--inline.loa").css("li")
            for i in range(len(authors)):
                data[f"author_{i}_name"] = extract_text(authors[i].get())
                data[f"author_{i}_link`"] = response.urljoin(
                    authors[i].css("a::attr(href)").get()
                )
            data["sourceurl"] = response.url
            data["baseurl"] = baseurl.format(0)
            yield data
        if pg < 100:
            if not self.endcheck(response):
                cb_kwargs = {
                    "baseurl": baseurl,
                    "pg": pg + 1,
                }
                yield scrapy.Request(
                    baseurl.format(pg + 1),
                    callback=self.parse,
                    meta=response.meta,
                    cb_kwargs=cb_kwargs,
                )

    def endcheck(self, response):
        if response.css("div.search-result__no-result").get():
            logging.info("last page reached")
            return True
        else:
            return False

    def artparse(self, response):
        inspect_response(response, self)
        response.meta
        data = {}
        data["title"] = extract_text(response.css("h1.citation__title").get())
        data["type_pub"] = extract_text(response.css("span.issue-heading").get())
        authors = response.css("li.loa__item")
        for i in range(len(authors)):
            data[f"author_{i}_name"] = extract_text(
                authors[i].css("span.loa__author-name").get()
            )
            data[f"author_{i}_affiliation"] = extract_text(
                authors[i].css("span.loa_author_inst").get()
            )
            data[f"author_{i}_link`"] = response.urljoin(
                authors[i].css("a.btn.blue::attr(href)").get()
            )

        journal = response.css("div.issue-item__detail")
        data["journal_name"] = extract_text(
            journal.css("span.epub-section__title").get()
        )
        data["journal_link"] = response.urljoin(journal.css("a::attr(href)").get())
        data["publication_date"] = extract_text(
            response.css("span.CitationCoverDate").get()
        )
        try:
            data["publication_year"] = parser.parse(data["publication_date"]).year
        except:
            data["publication_year"] = None
        data["citations"] = extract_text(
            response.css("span.citation").css("span").get()
        )
        data["downloads"] = extract_text(response.css("span.metric").css("span").get())
        data["abstract"] = extract_text(response.css("div.abstractSection").get())
        data["n_references"] = len(
            response.css("div.article__section.article__references").css("li")
        )
        nodesl1 = response.css("ol.rlist.level-1")
        indexterms = nodesl1.css("li")
        for i in range(len(indexterms)):
            # ignore levels for now
            data[f"indexterm_{i}"] = extract_text(indexterms[i].css("p").get())
