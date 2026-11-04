import xml.etree.ElementTree as ET
import urllib.request
import os
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

FEED_URL = "https://www.dailythanthi.com/stories.rss"
FILE_NAME = "feed.xml"
MAX_ITEMS = 100

TARGET_CATEGORY = "தமிழக செய்திகள் (Tamilnadu)"

print("Starting RSS filter script...")

if os.path.exists(FILE_NAME):
    try:
        tree = ET.parse(FILE_NAME)
        root = tree.getroot()
        channel = root.find("channel")
    except Exception:
        rss_str = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><title>Daily Thanthi - Tamilnadu News</title></channel></rss>'
        root = ET.fromstring(rss_str)
        channel = root.find("channel")
else:
    rss_str = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><title>Daily Thanthi - Tamilnadu News</title></channel></rss>'
    root = ET.fromstring(rss_str)
    channel = root.find("channel")

items_dict = {}

def parse_date(date_str):
    if not date_str:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)

if channel is not None:
    for item in channel.findall("item"):
        item_id = item.findtext("guid") or item.findtext("link")
        pub_date = parse_date(item.findtext("pubDate"))
        if item_id:
            items_dict[item_id] = (item, pub_date)

try:
    req = urllib.request.Request(
        FEED_URL, 
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        }
    )
    with urllib.request.urlopen(req) as response:
        new_data = response.read()
        
    new_root = ET.fromstring(new_data)
    
    entries = []
    for elem in new_root.iter():
        if elem.tag.endswith("entry") or elem.tag.endswith("item"):
            entries.append(elem)

    matched_count = 0
    for entry in entries:
        category_matched = False
        
        for elem in entry.iter():
            if elem.tag.endswith("category"):
                term = elem.attrib.get("term", "")
                label = elem.attrib.get("label", "")
                text = elem.text or ""
                
                target_lower = TARGET_CATEGORY.strip().lower()
                if (target_lower in term.strip().lower() or 
                    target_lower in label.strip().lower() or 
                    target_lower in text.strip().lower()):
                    category_matched = True
                    break

        if not category_matched:
            continue

        matched_count += 1
        
        title, link, guid, date_str, content_text = "", "", "", "", ""
        
        #
