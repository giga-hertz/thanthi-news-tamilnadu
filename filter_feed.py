import urllib.request
import xml.dom.minidom as minidom
import sys

RSS_URL = "https://www.dailythanthi.com/stories.rss"
TARGET_CATEGORY = "தமிழக செய்திகள் (Tamilnadu)"
OUTPUT_FILE = "feed.xml"

def fetch_and_filter():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }
    
    request = urllib.request.Request(RSS_URL, headers=headers)
    
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw_xml = response.read()
    except Exception as e:
        print(f"Error downloading RSS feed: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse XML while preserving CDATA, tags, and namespaces
    dom = minidom.parseString(raw_xml)
    channel = dom.getElementsByTagName("channel")[0]
    items = list(channel.getElementsByTagName("item"))

    retained_count = 0
    for item in items:
        # Check all <category> elements in the item
        categories = item.getElementsByTagName("category")
        matched = False
        
        for cat in categories:
            # Extract combined text/CDATA node values
            cat_text = "".join(
                c.nodeValue for c in cat.childNodes 
                if c.nodeType in (c.TEXT_NODE, c.CDATA_SECTION_NODE)
            ).strip()
            
            if cat_text == TARGET_CATEGORY or TARGET_CATEGORY in cat_text:
                matched = True
                break

        if matched:
            retained_count += 1
        else:
            # Clean up whitespace node preceding the item for clean XML formatting
            prev = item.previousSibling
            if prev and prev.nodeType == prev.TEXT_NODE and prev.nodeValue.strip() == "":
                channel.removeChild(prev)
            channel.removeChild(item)

    # Write output encoded in UTF-8
    with open(OUTPUT_FILE, "wb") as f:
        f.write(dom.toxml(encoding="utf-8"))

    print(f"Filtering complete: Retained {retained_count} of {len(items)} items. Saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    fetch_and_filter()
