## Chtaba scraper

Scrape Facebook page post links, then fetch each post's text and public comments using Selenium attached to a logged‑in Chrome session via remote debugging.

### Features
- **Post links extraction**: Scrolls a Facebook page and collects unique post URLs.
- **Post + comments scraping**: Opens each post and extracts the main post text and visible comments.
- **NDJSON output**: Writes one JSON object per line for easy downstream processing.

### Requirements
- Python 3.9+
- Google Chrome (recent version)
- ChromeDriver (Selenium 4 will auto-manage via Selenium Manager in most cases)
- A Facebook account logged in within the Chrome instance you attach to

Python dependencies are listed in `requirements.txt`:
- `selenium`
- `tqdm`

### Setup
1) Create and activate a virtual environment, then install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Start Chrome with remote debugging enabled (macOS example):

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="/tmp/chrome-fb-scraper"
```

- In that Chrome window, log into Facebook so pages and posts are accessible.
- The code expects the debugger address at `localhost:9222`.

### Usage
There are two steps: extract post links from a page, then scrape each post and its comments.

#### 1) Extract post links
Script: `links_extractor.py`

- Edit the `page_url`, `number_posts`, and `save_path` in the `if __name__ == "__main__":` block as needed.
- Then run:

```bash
python links_extractor.py
```

This produces a JSON file (default `post_links.json`) like:

```json
{
  "page_url": "https://www.facebook.com/SomePage",
  "total_posts_found": 10,
  "post_links": [
    "https://www.facebook.com/SomePage/posts/pfbid...",
    "https://www.facebook.com/SomePage/permalink/1234567890"
  ],
  "scraped_at": "2025-01-01 12:34:56"
}
```

#### 2) Scrape posts and comments
Script: `main.py`

- Ensure `main.py` points to the links file you created (default expects `post_links.json`).
- Run:

```bash
python main.py
```

This writes one object per line to `barca_posts_comments.json` (NDJSON). Each line has the form:

```json
{"post_text": "...", "comments": ["comment 1", "comment 2", "..."]}
```

### Programmatic usage
You can also call the classes directly:

```python
import json
from links_extractor import FacebookPostLinkExtractor
from post_scraper import FacebookPostScraper

page_url = "https://www.facebook.com/BarcaMoroccanFans"

# Step 1: collect links
link_extractor = FacebookPostLinkExtractor()
link_extractor.scrape_page_post_links(
    page_url=page_url,
    number_posts=10,
    save_path="post_links.json",
)

with open("post_links.json", "r") as f:
    post_links = json.load(f)["post_links"]

# Step 2: scrape posts + comments
scraper = FacebookPostScraper()
for url in post_links:
    data = scraper.scrape_post_and_comments(post_url=url)
    # write NDJSON line
    with open("posts_comments.ndjson", "a", encoding="utf-8") as out:
        out.write(json.dumps(data, ensure_ascii=False) + "\n")
```

### Project structure
- `links_extractor.py`: Extracts post URLs from a Facebook page (scroll + DOM scan + filtering).
- `post_scraper.py`: Opens a single post and scrapes the main text and visible comments.
- `main.py`: Reads `post_links.json` and writes scraped post/comment objects as NDJSON.
- `requirements.txt`: Python dependencies.
- `lab.ipynb`: Scratchpad/experiments (optional).

### Tips and troubleshooting
- **Remote debugging**: If you see connection errors like "cannot connect to chrome at localhost:9222", make sure Chrome is running with `--remote-debugging-port=9222` and that the port matches the code.
- **Login required**: Ensure the debug Chrome window is logged into Facebook; otherwise, content may be blocked.
- **ChromeDriver/Selenium**: Modern Selenium auto-manages the driver, but ensure Chrome is up-to-date. If needed, install a compatible ChromeDriver and put it on your PATH.
- **Selectors can change**: Facebook UI changes may break selectors used to find the post text or comments. Update the XPaths/CSS selectors in `post_scraper.py` if scraping yields empty results.
- **Performance**: Long pages and posts with many comments may take time. You can adjust sleeps/delays in the code to balance speed vs reliability.

### Ethical and legal considerations
- Respect Facebook's Terms of Service and robots directives.
- Only scrape data you are authorized to access. Obtain consent where appropriate.
- Avoid high request volumes and add delays to prevent disruption.
- Use the data responsibly and for legitimate purposes (e.g., research).

### License
No license specified. If you plan to share or publish this project, consider adding a license file.


