import os
import sys
import urllib.request
import email.utils
import xml.dom.minidom as minidom

RSS_URL = "https://www.dailythanthi.com/stories.rss"
TARGET_CATEGORY = "தமிழக செய்திகள் (Tamilnadu)"
OUTPUT_FILE = "myfeed.xml"
MAX_ITEMS = 400

def get_text_content(element):
    """Extract text or CDATA node contents cleanly."""
    return "".join(
        c.nodeValue for c in element.childNodes 
        if c.nodeType in (c.TEXT_NODE, c.CDATA_SECTION_NODE)
    ).strip()

def get_item_identifier(item):
    """Identify an article uniquely using guid, link, or title."""
    for tag in ("guid", "link", "title"):
        elems = item.getElementsByTagName(tag)
        if elems:
            val = get_text_content(elems[0])
            if val:
                return f"{tag}:{val}"
    return None

def matches_category(item, target):
    """Check if the item belongs to the target category."""
    for cat in item.getElementsByTagName("category"):
        if target in get_text_content(cat):
            return True
    return False

def update_channel_build_date(dom, channel):
    """Update or add <lastBuildDate> in RFC 822 format."""
    build_dates = channel.getElementsByTagName("lastBuildDate")
    rfc_date = email.utils.formatdate(usegmt=True)
    if build_dates:
        build_dates[0].firstChild.nodeValue = rfc_date
    else:
        new_tag = dom.createElement("lastBuildDate")
        new_tag.appendChild(dom.createTextNode(rfc_date))
        channel.insertBefore(new_tag, channel.firstChild)

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }
    
    req = urllib.request.Request(RSS_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw_fetched_xml = resp.read()
    except Exception as e:
        print(f"Error downloading RSS feed: {e}", file=sys.stderr)
        sys.exit(1)

    fetched_dom = minidom.parseString(raw_fetched_xml)
    fetched_channel = fetched_dom.getElementsByTagName("channel")[0]
    fetched_items = list(fetched_channel.getElementsByTagName("item"))

    # Determine whether myfeed.xml already exists
    if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
        try:
            dom = minidom.parse(OUTPUT_FILE)
            channel = dom.getElementsByTagName("channel")[0]
            is_initial_run = False
        except Exception:
            dom = fetched_dom
            channel = fetched_channel
            is_initial_run = True
    else:
        dom = fetched_dom
        channel = fetched_channel
        is_initial_run = True

    if is_initial_run:
        # First-ever run: filter fetched feed directly
        for item in fetched_items:
            if not matches_category(item, TARGET_CATEGORY):
                prev = item.previousSibling
                if prev and prev.nodeType == prev.TEXT_NODE and prev.nodeValue.strip() == "":
                    channel.removeChild(prev)
                channel.removeChild(item)
    else:
        # Subsequent runs: identify and insert only new matching items
        existing_items = list(channel.getElementsByTagName("item"))
        existing_ids = {get_item_identifier(it) for it in existing_items if get_item_identifier(it)}

        new_items_to_add = []
        for item in fetched_items:
            if matches_category(item, TARGET_CATEGORY):
                item_id = get_item_identifier(item)
                if item_id and item_id not in existing_ids:
                    new_items_to_add.append(item)

        print(f"Discovered {len(new_items_to_add)} new matching articles.")

        if not new_items_to_add:
            print("No new articles to add.")
            return

        # Insert new items at the top of the feed to keep newest articles first
        first_existing = existing_items[0] if existing_items else None
        for item in new_items_to_add:
            imported = dom.importNode(item, deep=True)
            if first_existing:
                channel.insertBefore(imported, first_existing)
                channel.insertBefore(dom.createTextNode("\n    "), first_existing)
            else:
                channel.appendChild(dom.createTextNode("\n    "))
                channel.appendChild(imported)

        update_channel_build_date(dom, channel)

    # Trim queue down to MAX_ITEMS (100) by removing the oldest items from the end
    all_items = list(channel.getElementsByTagName("item"))
    if len(all_items) > MAX_ITEMS:
        for excess_item in all_items[MAX_ITEMS:]:
            prev = excess_item.previousSibling
            if prev and prev.nodeType == prev.TEXT_NODE and prev.nodeValue.strip() == "":
                channel.removeChild(prev)
            channel.removeChild(excess_item)
        print(f"Trimmed feed to keep the maximum limit of {MAX_ITEMS} items.")

    with open(OUTPUT_FILE, "wb") as f:
        f.write(dom.toxml(encoding="utf-8"))

    final_count = len(channel.getElementsByTagName("item"))
    print(f"Updated {OUTPUT_FILE} successfully. Total items in feed: {final_count}")

if __name__ == "__main__":
    main()
