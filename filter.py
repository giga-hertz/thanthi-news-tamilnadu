import xml.etree.ElementTree as ET
import urllib.request
import os
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# 1. Configuration
FEED_URL = "https://www.dailythanthi.com/stories.rss"
FILE_NAME = "feed.xml"
MAX_ITEMS = 100

# தமிழக செய்திகளுக்கான Category Terms & Keywords
ALLOWED_CATEGORIES = {"tamilnadu", "tamil-nadu", "tamil nadu", "தமிழக செய்திகள்"}
TITLE_KEYWORDS = {"தமிழ்நாடு", "தமிழக"}

# 2. Load existing feed
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

# Load existing items
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
    
    # Atom entries
    entries = new_root.findall(".//{http://www.w3.org/2005/Atom}entry") or new_root.findall(".//entry")
    
    for entry in entries:
        title = entry.findtext("{http://www.w3.org/2005/Atom}title") or entry.findtext("title") or ""
        link_elem = entry.find("{http://www.w3.org/2005/Atom}link") or entry.find("link")
        link = link_elem.attrib.get("href") if link_elem is not None and "href" in link_elem.attrib else (link_elem.text if link_elem is not None else "")
        
        # Extract categories (term & label)
        categories = []
        for elem in list(entry):
            if elem.tag.endswith("category"):
                term = elem.attrib.get("term") or elem.attrib.get("label") or elem.text
                if term:
                    categories.append(term.strip().lower())

        # Check Category Match or Title/Link Keyword Match
        category_match = any(cat in ALLOWED_CATEGORIES for cat in categories)
        url_match = any(kw in link.lower() for kw in ALLOWED_CATEGORIES)
        title_match = any(kw in title for kw in TITLE_KEYWORDS)

        # If none of them match, skip the article
        if not (category_match or url_match or title_match):
            continue

        guid = entry.findtext("{http://www.w3.org/2005/Atom}id") or entry.findtext("id") or link
        date_str = entry.findtext("{http://www.w3.org/2005/Atom}published") or entry.findtext("published") or entry.findtext("{http://www.w3.org/2005/Atom}updated") or entry.findtext("updated")
        
        dt = parse_date(date_str)
        
        item_elem = ET.Element("item")
        ET.SubElement(item_elem, "title").text = title.strip()
        ET.SubElement(item_elem, "link").text = link.strip()
        ET.SubElement(item_elem, "guid").text = guid.strip()
        ET.SubElement(item_elem, "pubDate").text = dt.strftime("%a, %d %b %Y %H:%M:%S %Z")
        
        if guid or link:
            items_dict[guid or link] = (item_elem, dt)

except Exception as e:
    print(f"Error fetching feed: {e}")

# 4. Sort and Limit
sorted_items = sorted(items_dict.values(), key=lambda x: x[1], reverse=True)
limited_items = sorted_items[:MAX_ITEMS]

# 5. Update Channel
if channel is not None:
    for item in channel.findall("item"):
        channel.remove(item)

    for item, dt in limited_items:
        channel.append(item)

# 6. Save File
tree = ET.ElementTree(root)
tree.write(FILE_NAME, encoding="utf-8", xml_declaration=True)
