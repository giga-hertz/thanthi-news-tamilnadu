import xml.etree.ElementTree as ET
import urllib.request
import os
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# 1. Configuration
FEED_URL = "https://www.dailythanthi.com/stories.rss"
FILE_NAME = "feed.xml"
MAX_ITEMS = 100
ALLOWED_CATEGORIES = set()  # Leave empty to keep all categories

# 2. Load existing accumulated feed if it exists, or create a new base structure
if os.path.exists(FILE_NAME):
    tree = ET.parse(FILE_NAME)
    root = tree.getroot()
    channel = root.find("channel")
else:
    rss_str = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Daily Thanthi Filtered Feed</title></channel></rss>'
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
for item in channel.findall("item"):
    item_id = item.findtext("guid") or item.findtext("link")
    pub_date = parse_date(item.findtext("pubDate"))
    if item_id:
        items_dict[item_id] = (item, pub_date)

# 3. Fetch and parse remote feed (Supports Atom <entry> and RSS <item>)
try:
    req = urllib.request.Request(
        FEED_URL, 
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req) as response:
        new_data = response.read()
        
    new_root = ET.fromstring(new_data)
    
    # Check for Atom entries or standard RSS items
    entries = new_root.findall(".//{http://www.w3.org/2005/Atom}entry") or new_root.findall("entry")
    items = new_root.findall(".//item")
    
    if entries:
        for entry in entries:
            title = entry.findtext("{http://www.w3.org/2005/Atom}title") or entry.findtext("title") or ""
            
            link_elem = entry.find("{http://www.w3.org/2005/Atom}link") or entry.find("link")
            link = link_elem.attrib.get("href") if link_elem is not None and "href" in link_elem.attrib else (link_elem.text if link_elem is not None else "")
            
            guid = entry.findtext("{http://www.w3.org/2005/Atom}id") or entry.findtext("id") or link
            date_str = entry.findtext("{http://www.w3.org/2005/Atom}published") or entry.findtext("published") or entry.findtext("{http://www.w3.org/2005/Atom}updated") or entry.findtext("updated")
            
            dt = parse_date(date_str)
            
            # Create a standard RSS item format for internal storage
            item_elem = ET.Element("item")
            ET.SubElement(item_elem, "title").text = title.strip()
            ET.SubElement(item_elem, "link").text = link.strip()
            ET.SubElement(item_elem, "guid").text = guid.strip()
            ET.SubElement(item_elem, "pubDate").text = dt.strftime("%a, %d %b %Y %H:%M:%S %Z")
            
            if guid or link:
                items_dict[guid or link] = (item_elem, dt)
                
    elif items:
        for item in items:
            item_id = item.findtext("guid") or item.findtext("link")
            dt = parse_date(item.findtext("pubDate"))
            if item_id:
                items_dict[item_id] = (item, dt)

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
