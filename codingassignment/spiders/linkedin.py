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

DATETIMENOW = datetime.now().strftime("%Y%m%d_%H%M%S")
HOMEDIR = os.path.expanduser("~")

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename=f"C:/Users/tlebr/Google Drive/Personal/codingassignment/logs/spider_{DATETIMENOW}.log",
    level=logging.INFO,
    )

class LinkedinSpider(scrapy.Spider):
    # create/update a single a master linkedin csv with info about each person
    # create a professional history csv for each perosn
    name = 'linkedin'
    custom_settings = {
        'ITEM_PIPELINES': {
            'codingassignment.pipelines.LinkedinPipeline': 300,
        }
    }

    def __init__(self, **kwargs):
        configure_logging(install_root_handler=False)

    def start_requests(self):
        # command: scrapy crawl linkedin -O data/linkedinmeta.py
        path = f"C:/Users/tlebr/Google Drive/Personal/codingassignment/data/linkedins/"
        start_urls = [f"{path}{f}" for f in os.listdir(path) if os.path.splitext(f"{path}{f}")[1] == ".html"]
        for f in start_urls:
            print(f)
            meta = {
                "filepath": f,
                # get justfilename (without extension)
                "filename": os.path.splitext(os.path.basename(f))[0],
                "scrape_time": datetime.utcfromtimestamp(os.path.getmtime(f))
            }
            yield scrapy.Request(f"file://{f}", callback=self.parse, meta=meta)

    def parse(self, response):
        meta = response.meta
        linkedinurl = re.search("(?<=Content-Location: )(.*)(?=\r\nSubject)", response.text[:500]).group(1).strip()
        meta["linkedin_name"] =  extract_text(response.xpath('//h1[contains(@class, "text-heading-xlarge")]').get())
        meta["linkedin_url"]  = linkedinurl
        about = response.xpath("//section[contains(@id, 'pv-profile-section')]").get()
        meta["about"] = extract_text(about)
        meta["name"] = extract_text(response.xpath("//h1[contains(@class, 'text-heading-xlarge')]").get())
        xpsect = response.xpath("//section[contains(@id, 'experience-section')]")
        xps = xpsect.xpath(".//li[contains(@class, 'pv-entity__position-group-pager')]")
        activitiesls = []
        for xp in xps: 
            activity = {}
            activity["linkedin_url"]  = linkedinurl
            activity["filename"]  = meta["filename"]
            # deal with nested job xp
            if len(xp.xpath(".//li")) > 0:
                org = xp.xpath(".//h3[contains(@class, 't-16')]")
                # span with class is hidden text saying 'dates employed'
                activity["organization"] = extract_text(org.xpath(".//span[not(@class)]").get())
                for li in xp.xpath(".//li"):
                    activity2 = activity.copy()
                    title = xp.xpath(".//h3[contains(@class, 't-14')]")
                    # span with class is hidden text saying 'dates employed'
                    activity2["title"] = extract_text(title.xpath(".//span[not(@class)]").get())
                    activity2["title"] = extract_text(li.css("h3").get())
                    activity2["fulltime"] = extract_text(xp.xpath("//span[contains(@class, 'pv-entity__secondary-title')]").get())
                    if activity2["fulltime"]:
                        activity2["fulltime"] = activity2["fulltime"].strip()
                    dtp = xp.xpath(".//h4[contains(@class, 'pv-entity__date-range')]")
                    # span with class is hidden text saying 'dates employed'
                    dt = extract_text(dtp.xpath(".//span[not(@class)]").get())
                    activity2 = self.dt_bio_location_type(activity2, li, dt, "experience")
                    logging.info(activity2)
                    activitiesls.append(activity2)
            # normal job experience
            else:
                activity["title"] = extract_text(xp.css("h3").get())
                activity["organization"] = extract_text(xp.xpath(".//p[contains(@class, 'pv-entity__secondary-title')]").get())
                activity["fulltime"] = extract_text(xp.xpath("//span[contains(@class, 'pv-entity__secondary-title')]").get())
                if activity["fulltime"]:
                    activity["fulltime"] = activity["fulltime"].strip()
                dtp = xp.xpath(".//h4[contains(@class, 'pv-entity__date-range')]")
                # span with class is hidden text saying 'dates employed'
                dt = extract_text(dtp.xpath(".//span[not(@class)]").get())
                activity = self.dt_bio_location_type(activity, xp, dt, "experience")
                activitiesls.append(activity)
                logging.info(activity)


        edusect = response.xpath("//section[contains(@id, 'education-section')]")
        edus = edusect.css("li")
        for edu in edus:
            activity = {}
            activity["linkedin_url"]  = linkedinurl
            activity["filename"]  = meta["filename"]
            activity["organization"] = edu.css("h3::text").get()
            if activity["organization"]:
                activity["organization"] = activity["organization"].replace("=\r\n", "")
            degreeinfo = edu.xpath(".//p[contains(@*, 'pv-entity__secondary-title')]")
            for info in degreeinfo:
                hiddenfield = extract_text(info.xpath(".//span[contains(@class, 'visually-hidden')]").get())
                if hiddenfield == "Degree Name":
                    activity["degree"] = extract_text(info.xpath(".//span[contains(@class, 'pv-entity__comma-item')]").get())
                elif hiddenfield == "Field Of Study":
                    activity["field_of_study"] = extract_text(info.xpath(".//span[contains(@class, 'pv-entity__comma-item')]").get())
            if activity.get("degree") and activity.get("field_of_study"):
                activity["title"] = f"{activity['degree']} in {activity['field_of_study']}" 
            elif activity.get("degree"):
                activity["title"] = f"{activity['degree']}"
            elif activity.get("field_of_study"):
                activity["title"] = f"{activity['field_of_study']}"
            else:
                activity["title"] = ""
            dtp = edu.xpath(".//p[contains(@class, 'pv-entity__dates')]")
            # span with class is hidden text saying 'dates employed'
            dt = extract_text(dtp.xpath(".//span[not(@class)]").get())
            activity = self.dt_bio_location_type(activity, edu, dt, "education")
            logging.info(activity)
            activitiesls.append(activity)
        master = {
            "meta": meta,
            "activities": activitiesls
        }
        return master


    def dt_bio_location_type(self, activity, xp, dt, typename):
        activity = activity.copy()
        # dt, bio, and location parsing functions are roughly the same
        # share across experiences (edu, xp, and cascading xp)
        activity["date_start"] = re.search("(.*)(?==E2=80=93)", dt)
        if activity["date_start"]:
            activity["date_start"] = activity["date_start"].group(1).strip()
        try:
            activity["date_start_asdt"] = parser.parse(activity["date_start"])
        except:
            activity["date_start_asdt"] = None
        activity["date_end"] = re.search("(?<=E2=80=93)(.*)", dt)
        if activity["date_end"]:
            activity["date_end"] = activity["date_end"].group(1).strip()
        else:
            activity["date_end"] = re.search("(?<=graduation=)(.*)", dt)
            if activity["date_end"]:
                activity["date_end"] = activity["date_end"].group(1).strip()

        if activity["date_end"] == "Present":
            activity["date_end_asdt"] = datetime.now()
        else:
            try:
                activity["date_end_asdt"] = parser.parse(activity["date_end"])
            except:
                activity["date_end_asdt"] = None
        # comes back in format '1 yr 5 mos' do conversion later
        activity["duration"] = extract_text(xp.xpath(".//span[contains(@class, 'pv-entity__bullet-item-v2')]").get())

        location = xp.xpath(".//h4[contains(@class, 'pv-entity__location')]")
        # span with class is hidden text saying 'dates employed'
        activity['location'] = location.xpath(".//span[not(@class)]/text()").get()
        # TODO: validate
        activity["biography"] = extract_text(xp.xpath(".//div[contains(@class, 'inline-show-more-text')]").get())
        if not activity["biography"]:
            activity["biography"] = extract_text(xp.xpath(".//div[contains(@class, 'pv-entity__extra-details')]").get())
        activity["type"] = typename
        return activity

