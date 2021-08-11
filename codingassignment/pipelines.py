# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from os import environ
from itemadapter import ItemAdapter
import pandas as pd

class CodingassignmentPipeline:
    
    def open_spider(self, spider):
        # assign dumb unique ids starting with zero. 
        self.uid = 0

    def process_item(self, item, spider):
        item["id"] = self.uid
        self.uid += 1
        return item


class LinkedinPipeline:
    
    def open_spider(self, spider):
        self.facultydf = pd.read_csv(
            r"C:/Users/tlebr/Google Drive/Personal/codingassignment/data/facultymain.csv", 
            encoding= 'unicode_escape',
        )

    def process_item(self, item, spider):
        meta = item.get("meta")
        activities = item.get("activities")
        # merge id onto activities dataframe
        df = pd.DataFrame(activities).merge(self.facultydf[["id", "linkedin"]], left_on="linkedin_url", right_on="linkedin", how="left")
        # save activities dataframe
        df.to_csv(f"data/linkedincsvs/{meta['filename']}.csv", encoding="utf-8")
        # merge id onto dataframe
        df2 = pd.DataFrame(meta, index=[0]).merge(self.facultydf[["id", "linkedin"]], left_on="linkedin_url", right_on="linkedin", how="left")
        meta = df2.to_dict(orient="list")
        for key, value in meta.items():
            meta[key] = value[0]
        return meta

