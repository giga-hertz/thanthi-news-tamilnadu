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
    
    # Universal search for entries regardless of namespace URI
    entries = []
    for elem in new_root.iter():
        if elem.tag.endswith("entry") or elem.tag.endswith("item"):
            entries.append(elem)
            
    print(f"Discovered {len(entries)} total items/entries in feed.")

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
        
        # Extract title, link, guid, date safely across namespaces
        title, link, guid, date_str = "", "", "", ""
        for child in entry:
            tag_name = child.tag.split('}')[-1].lower()
            if tag_name == "title":
                title = child.text or ""
            elif tag_name == "link":
                link = child.attrib.get("href") or child.text or ""
            elif tag_name in ("id", "guid"):
                guid = child.text or ""
            elif tag_name in ("published", "updated", "pubdate"):
                date_str = child.text or ""

        if not guid:
            guid = link

        dt = parse_date(date_str)
        
        item_elem = ET.Element("item")
        ET.SubElement(item_elem, "title").text = title.strip()
        ET.SubElement(item_elem, "link").text = link.strip()
        ET.SubElement(item_elem, "guid").text = guid.strip()
        ET.SubElement(item_elem, "pubDate").text = dt.strftime("%a, %d %b %Y %H:%M:%S %Z")
        
        if guid or link:
            items_dict[guid or link] = (item_elem, dt)

    print(f"Matched {matched_count} items with target category.")

except Exception as e:
    print(f"Error fetching feed: {e}")

sorted_items = sorted(items_dict.values(), key=lambda x: x[1], reverse=True)
limited_items = sorted_items[:MAX_ITEMS]

if channel is not None:
    for item in channel.findall("item"):
        channel.remove(item)

    for item, dt in limited_items:
        channel.append(item)

tree = ET.ElementTree(root)
tree.write(FILE_NAME, encoding="utf-8", xml_declaration=True)
print(f"Successfully wrote {len(limited_items)} items to {FILE_NAME}.")
