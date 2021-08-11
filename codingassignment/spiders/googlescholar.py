import scrapy
from urllib.parse import urlparse
from html_text import extract_text
import pandas as pd
import os
from datetime import datetime
import re
from dateutil import parser
import logging
from scrapy.utils.log import configure_logging
from scrapy.shell import inspect_response



DATETIMENOW = datetime.now().strftime("%Y%m%d_%H%M%S")
# HOMEDIR = os.path.expanduser("~")

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename=f"C:/Users/tlebr/Google Drive/Personal/codingassignment/logs/googlescholarspider_{DATETIMENOW}.log",
    level=logging.INFO,
    )

class GoogleScholarSpider(scrapy.Spider):
    # command: scrapy crawl GS -O data/googlescholarmeta.py

    # create/update a single a master linkedin csv with info about each person
    # create a professional history csv for each perosn
    name = 'GS'

    def __init__(self, **kwargs):
        configure_logging(install_root_handler=False)
        self.facultydf = pd.read_csv(
            r"C:/Users/tlebr/Google Drive/Personal/codingassignment/data/facultymain.csv",
            encoding="unicode_escape",
        )

    def start_requests(self):
        path = f"C:/Users/tlebr/Google Drive/Personal/codingassignment/data/googlescholars/"
        start_urls = [f"{path}{f}" for f in os.listdir(path) if os.path.splitext(f"{path}{f}")[1] == ".html"]
        for f in start_urls:
            print(f)
            cb_kwargs = {
                "data" : {
                "filepath": f,
                # get justfilename (without extension)
                "filename": os.path.splitext(os.path.basename(f))[0],
                "scrape_time": datetime.utcfromtimestamp(os.path.getmtime(f))
                }
            }
            # time = datetime.datetime.fromtimestamp(fname.stat().st_mtime)
            yield scrapy.Request(f"file://{f}", callback=self.parse, cb_kwargs=cb_kwargs)

    def parse(self, response, data):
        googlescholarurl = re.search("(?=https)(.*)(?= -->)", response.text[:500]).group(1).strip()
        data["googlescholar_url"] = googlescholarurl
        df2 = pd.DataFrame(data, index=[0]).merge(self.facultydf[["id", "googlescholar"]], left_on="googlescholar_url", right_on="googlescholar", how="left")
        data = df2.to_dict(orient="list")
        for key, value in data.items():
            data[key] = value[0]
        data['googlescholar_name'] = extract_text(response.xpath(".//div[contains(@id, 'gsc_prf_in')]").get())
        tablebody = response.xpath("//tbody[contains(@id, 'gsc_a_b')]")
        articles = tablebody.css("tr")
        metals = []
        for article in articles:
            meta = data.copy()
            meta["cited_by"] = extract_text(article.css("a.gsc_a_ac.gs_ibl").get())
            meta["year"] = extract_text(article.css("span.gsc_a_h.gsc_a_hc.gs_ibl").get())
            meta["title"] = extract_text(article.css("a.gsc_a_at").get())
            meta["article_link"] = article.css("a.gsc_a_at::attr(href)").get()
            divs = article.css("div.gs_gray")
            for div in divs:
                text = extract_text(div.get())
                # if numbers in string, assume its publication info and not authors
                if re.search('\d', text):
                    meta["publication"] = text
                else:
                    meta["authors"] = text
            metals.append(meta)
        logging.info(f"saving to data/googescholarscsvs/{meta['googlescholar_name']}.csv ..")
        logging.info(metals)
        pd.DataFrame(metals).to_csv(f"data/googescholarscsvs/{meta['googlescholar_name']}.csv", encoding="utf-8")

        self.get_coauthors(response, name=meta['googlescholar_name'])
        data2 = data.copy()
        data2 = self.get_details(response, data2)
        data2 = self.get_stats(response, data2)
        data2 = self.citations_by_year(response, data2)
        yield data2



    def get_details(self, response, data=None):
        if not data:
            data = {}
        data['googlescholar_interests'] = [extract_text(x.get()) for x in response.xpath(".//div[contains(@id, 'gsc_prf_int')]//a")]
        data['googlescholar_postition'] = extract_text(response.css("div.gsc_prf_il").get())
        data['googlescholar_homepage'] = response.xpath(".//div[contains(@id, 'gsc_prf_ivh')]//a/@href").get()
        return data

    def get_coauthors(self, response, name):
        coauthors = response.css("ul.gsc_rsb_a").css("li")
        datals = []
        for author in coauthors:
            data = {}
            data["facultymember"] = name
            data["coauthor"] = extract_text(author.css("a").get())
            data["coauthor_link"] = author.css("a::attr(href)").get()
            data["coauthor-affiliation"] = extract_text(author.css("span.gsc_rsb_a_ext").get())
            datals.append(data)
        pd.DataFrame(datals).to_csv(f"data/googlescholarscoauthors/{name}.csv", encoding="utf-8")

    def get_stats(self, response, data=None):
        # three row table with: 
        # citaitons, hindex, i10 index
        if not data:
            data = {}
        table = response.xpath(".//table[contains(@id, 'gsc_rsb_st')]//tr")
        data["citations_total"] = extract_text(table[1].css("td.gsc_rsb_std").get())
        data["citations_2016"] = extract_text(table[1].css("td.gsc_rsb_std")[1].get())
        data["h-index_total"] = extract_text(table[2].css("td.gsc_rsb_std").get())
        data["h-index_2016"] = extract_text(table[2].css("td.gsc_rsb_std")[1].get())
        data["i10-index_total"] = extract_text(table[3].css("td.gsc_rsb_std").get())
        data["i10-index_2016"] = extract_text(table[3].css("td.gsc_rsb_std")[1].get())
        return data

    def citations_by_year(self, response, data=None):
        if not data:
            data = {}
        hist = response.css("div.gsc_md_hist_w")
        years = hist.css("span.gsc_g_t")
        values = hist.css("span.gsc_g_al")
        if len(years) != len(values):
            logging.error("cannot compare years and values bc diff vlaues")
            return None
        for i in range(len(years)):
            data[extract_text(years[i].get())] = extract_text(values[i].get())
        return data




        






















    #     df = pd.read_csv(
    #         r"C:/Users/tlebr/Google Drive/Personal/codingassignment/data/facultymain.csv", 
    #         encoding= 'unicode_escape',
    #     )
    #     #  remove nas and remove any flags between user and citation to pass robots.txt requirement
    #     start_urls = df.googlescholar[df.googlescholar.notna()].str.replace("citations?.*?user", "citations?user")
    #     for url in start_urls:
    #         self.url = url + "&view_op=list_works&pagesize=100"
    #         yield scrapy.Request(self.url.format(), callback=self.parse)
            
    #     # [print(a) for a in start_urls.apply(usercut)]
    #     # for url in start_urls:
    #     # path = f"C:/Users/tlebr/Google Drive/Personal/codingassignment/data/linkedins/"
    #     # # path = "data/linkedins/"
    #     # start_urls = [f"{path}{f}" for f in os.listdir(path) if os.path.splitext(f"{path}{f}")[1] == ".html"]
    #     # # files = os.listdir("data/linkedins/")
    
    # def parse(self, response):
    #     tablebody = response.xpath("//tbody[contains(@id, 'gsc_a_b')]")
    #     articles = tablebody.css("tr")
    #     for article in articles:
    #         data = {}
    #         data["cited_by"] = extract_text(article.css("a.gsc_a_ac.gs_ibl").get())
    #         data["year"] = extract_text(article.css("span.gsc_a_h.gsc_a_hc.gs_ibl").get())
    #         data["title"] = extract_text(article.css("a.gsc_a_at").get())
    #         divs = article.css("div.gs_gray")
    #         for div in divs:
    #             text = extract_text(div.get())
    #             # if numbers in string, assume its publication info and not authors
    #             if re.search('\d', text):
    #                 data["publication"] = text
    #             else:
    #                 data["authors"] = text
    #         yield data
    #             # any(char.isdigit() for char in extract_text(div.get()) 

    # def formatstarturl(url):
    #     self.url = f"{url}&view_op=list_works&sortby=pubdate&cstart={self.cstart}&pagesize=100"

    #     url += "&view_op=list_works&sortby=pubdate&"

    # def endcheck(self, response):
    #     articletxt = extract_text(response.xpath("//span[contains(@id, 'gsc_a_nn')]").get())
    #     nums = articletxt.split(" ")[-1]
    #     if nums != "1-100":
    #         return False
    #     else:
    #         return True

    # # def usercut(x):
    # #     # transforms google scholar ids to standardize them. 
    # #     ind = x.find("user=")
    # #     if ind > 0:
    # #         endind = x[ind:].find("&")
    # #         if endind > 0:
    # #             x = x[:ind]
    # #     return x