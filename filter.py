import xml.etree.ElementTree as ET
import urllib.request
import os
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# 1. Configuration
FEED_URL = "https://www.dailythanthi.com/stories.rss"  # <-- Put your raw source RSS feed URL here
FILE_NAME = "feed.xml"
MAX_ITEMS = 100

# 🌟 PUT THE CATEGORIES YOU WANT TO KEEP HERE (case-insensitive)
ALLOWED_CATEGORIES = {"தமிழக செய்திகள் (Tamilnadu)"} 
# Leave it empty set if you want to allow everything: ALLOWED_CATEGORIES = set()

# 2. Load existing accumulated feed if it exists, or create a new base structure
if os.path.exists(FILE_NAME):
    tree = ET.parse(FILE_NAME)
    root = tree.getroot()
    channel = root.find("channel")
else:
    rss_str = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>My Filtered Feed</title></channel></rss>'
    root = ET.fromstring(rss_str)
    channel = root.find("channel")

items_dict = {}

def parse_item_date(item):
    pub_date_text = item.findtext("pubDate")
    if pub_date_text:
        try:
            return parsedate_to_datetime(pub_date_text)
        except Exception:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)

# Load existing items into dictionary
for item in channel.findall("item"):
    item_id = item.findtext("guid") or item.findtext("link")
    if item_id:
        items_dict[item_id] = (item, parse_item_date(item))

# 3. Fetch the latest feed data and apply category filter
try:
    req = urllib.request.urlopen(FEED_URL)
    new_data = req.read()
    new_root = ET.fromstring(new_data)
    new_channel = new_root.find("channel")
    
    if new_channel is not None:
        for item in new_channel.findall("item"):
            # Extract categories from the item
            item_categories = {c.text.strip().lower() for c in item.findall("category") if c.text}
            
            # Filter check: If categories are specified, skip items that don't match
            if ALLOWED_CATEGORIES and not item_categories.intersection(ALLOWED_CATEGORIES):
                continue

            item_id = item.findtext("guid") or item.findtext("link")
            if item_id:
                items_dict[item_id] = (item, parse_item_date(item))
except Exception as e:
    print(f"Error fetching feed: {e}")

# 4. Sort items by date descending (newest first) and limit to MAX_ITEMS (100)
sorted_items = sorted(items_dict.values(), key=lambda x: x[1], reverse=True)
limited_items = sorted_items[:MAX_ITEMS]

# 5. Clear existing items from channel and re-add the sorted, limited list
for item in channel.findall("item"):
    channel.remove(item)

for item, dt in limited_items:
    channel.append(item)

# 6. Save the updated XML back to the file
tree = ET.ElementTree(root)
tree.write(FILE_NAME, encoding="utf-8", xml_declaration=True)
