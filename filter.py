import xml.etree.ElementTree as ET
import urllib.request
import os
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# 1. Configuration
FEED_URL = "https://www.dailythanthi.com/stories.rss"
FILE_NAME = "feed.xml"
MAX_ITEMS = 100

# Target category string inside <category>
TARGET_CATEGORY = "தமிழக செய்திகள் (Tamilnadu)"

# 2. Load existing accumulated feed if it exists, or create base RSS structure
if os.path.exists(FILE_NAME):
    try:
        tree = ET.parse(FILE_NAME)
        root = tree.getroot()
        channel = root.find("channel")
    except Exception:
        rss_str = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Daily Thanthi - Tamilnadu News</title></channel></rss>'
        root = ET.fromstring(rss_str)
        channel = root.find("channel")
else:
    rss_str = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Daily Thanthi - Tamilnadu News</title></channel></rss>'
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

# Load existing items from local feed.xml
if channel is not None:
    for item in channel.findall("item"):
        item_id = item.findtext("guid") or item.findtext("link")
        pub_date = parse_date(item.findtext("pubDate"))
        if item_id:
            items_dict[item_id] = (item, pub_date)

# 3. Fetch remote feed
try:
    req = urllib.request.Request(
        FEED_URL, 
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req) as response:
        new_data = response.read()
        
    new_root = ET.fromstring(new_data)
    
    entries = new_root.findall(".//{http://www.w3.org/2005/Atom}entry") or new_root.findall(".//entry")
    
    for entry in entries:
        category_matched = False
        
        # Scan category elements for term, label, or inner text matching TARGET_CATEGORY
        for elem in list(entry):
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

        
