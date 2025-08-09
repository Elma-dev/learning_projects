

from selenium import webdriver
from selenium.webdriver import ChromeOptions
import time
import re
import json

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

class FacebookPostLinkExtractor():
    def __init__(self):
        self.driver = self.open_chrome()
        self.post_links = set()
        self.page_id = None

    def open_chrome(self):
        chrome_options= ChromeOptions()
        chrome_options.debugger_address= "localhost:9222"
        return webdriver.Chrome(options=chrome_options)
    
    def is_valid_post_link(self,url):
        """Checks if a URL is a valid Facebook post link."""
        if not url:
            return False
        
        # Check if it's a Facebook URL
        if 'facebook.com' not in url:
            return False
        
        # Check for common post URL patterns
        post_patterns = [
            r'/posts/',
            r'/share/p/',
            r'story_fbid=',
            r'/permalink/',
            r'/photo\.php\?fbid='
        ]

        return any(re.search(pattern, url) for pattern in post_patterns)
    
    def clean_facebook_url(self,url):
        """Cleans Facebook URLs by removing tracking parameters."""
        try:
            # Remove common tracking parameters
            tracking_params = ['__cft__', '__tn__', 'ref', 'refid', 'hc_ref', 'fref']
            
            if '?' in url:
                base_url, params = url.split('?', 1)
                param_pairs = params.split('&')
                
                # Keep only non-tracking parameters
                clean_params = []
                for param in param_pairs:
                    if '=' in param:
                        key = param.split('=')[0]
                        if key not in tracking_params:
                            clean_params.append(param)
                
                if clean_params:
                    return f"{base_url}?{'&'.join(clean_params)}"
                else:
                    return base_url
            
            return url
        except Exception:
            return url


    def extract_post_links(self):
        """Extracts all post links from the current page."""
        print(f"{GREEN}[INFO] Extracting post links...{RESET}")
        try:
            js_script = """
                const anchors = Array.from(document.querySelectorAll("a[href]"));
                const postRegexes = [
                    /\\/posts\\/(pfbid[\\w]+)/i,
                    /\\/permalink\\/\\d+/i,
                    /story_fbid=\\d+/i,
                    /\\/photo\\.php\\?fbid=\\d+/i,
                    /\\/videos\\/\\d+/i,
                    /\\/reel\\/\\d+/i
                ];
                const links = new Set();

                for (const a of anchors) {
                    const href = a.href;
                    if (!href || !href.includes("facebook.com") || !href.includes('"""+self.page_id+"""')) continue;

                    for (const regex of postRegexes) {
                        if (regex.test(href)) {
                            links.add(href.split('?')[0]); // strip tracking
                            break;
                        }
                    }
                }

                return Array.from(links);
            """

            
            js_links = self.driver.execute_script(js_script)
            
            for link in js_links:
                if self.is_valid_post_link(link):
                    clean_url = self.clean_facebook_url(link)
                    self.post_links.add(clean_url)
        except Exception as e:
            print(f"{RED}[Error] extracting post links: {e}{RESET}")
        
    def scroll_page_to_load_posts(self,number_posts=None):
        """Scrolls the page to load more posts."""
        print(f"{GREEN}[INFO] Start Scrolling...{RESET}")
        i=0
        count_nb_e=0
        bsh_previous=-1
        bsh_current=1
        while(True):
            bsh_current=self.driver.execute_script(f"window.scrollTo(document.body.scrollHeight * {(i)/50}, document.body.scrollHeight * {(i+2)/50 }); console.log(document.body.scrollHeight); return  document.body.scrollHeight;")
            if bsh_current==bsh_previous:
                count_nb_e+=1
                if count_nb_e==50:
                    break
            else:
                count_nb_e=0
            bsh_previous = bsh_current
            self.extract_post_links()
            print(f"Number of extracted links: {len(self.post_links)}")
            if number_posts and len(self.post_links)>=number_posts:
                break
            i+=1
            time.sleep(3)
    
    def scrape_page_post_links(self,page_url,number_posts=None,save_path="facebook_post_links.json"):
        """Main function to scrape post links from a Facebook page."""
        print(f"{GREEN}[INFO] Navigating to page: {page_url}{RESET}")
        self.page_id = page_url.split("/")[-1]
        self.driver.get(page_url)
        time.sleep(5)
        # Scroll to load more posts
        self.scroll_page_to_load_posts(number_posts=number_posts)
        print(f"{GREEN}[INFO] End of scrolling{RESET}")
        print(f"{GREEN}[INFO] End extract post links...{RESET}")
        print(f"{GREEN}[INFO] {len(self.post_links)} links Extracted{RESET}")
        results = {
            "page_url": page_url,
            "total_posts_found": len(self.post_links),
            "post_links": list(self.post_links),
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(save_path, "w", encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"{GREEN}[INFO] Links saved{RESET}")



if __name__=="__main__":
    facebook_scraper = FacebookPostLinkExtractor()
    facebook_scraper.scrape_page_post_links("https://www.facebook.com/BarcaMoroccanFans",number_posts=10,save_path="post_links.json")