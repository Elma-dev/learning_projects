import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm
import json
import re
from urllib.parse import urljoin, urlparse
from utils import open_chrome

# ANSI escape codes for colors
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

# Change this to the Facebook page you want to scrape
PAGE_URL = "https://www.facebook.com/profile.php?id=100013455673667" #"https://www.facebook.com/jafiklblan20"

# # --- SETUP THE BROWSER ---
# chrome_options = Options()
# chrome_options.add_argument("--disable-notifications")
# # Optional: run in headless mode (no GUI)
# #chrome_options.add_argument("--headless")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")
# chrome_options.add_argument("--window-size=1920,1080")

# print("Setting up WebDriver...")
# service = Service(ChromeDriverManager().install())
# driver = webdriver.Chrome(service=service, options=chrome_options)
# driver.implicitly_wait(10)
# wait = WebDriverWait(driver, 20)
# FB_EMAIL="elmajjodi2@gmail.com"
# FB_PASSWORD="izm123khanz"
driver = open_chrome()

def login():
    """Logs into Facebook."""
    print(f"{GREEN}Navigating to Facebook login page...{RESET}")
    driver.get("https://www.facebook.com")

    # Handle cookie consent button if it appears
    # try:
    #     # The button might have different data-testid values, check the one on your page
    #     cookie_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='cookie-policy-manage-dialog-accept-button']")
    #     print("Accepting cookies...")
    #     cookie_button.click()
    #     time.sleep(1)
    # except NoSuchElementException:
    #     print("Cookie consent button not found, continuing...")

    print(f"{GREEN}Entering credentials...{RESET}")
    email_input = driver.find_element(By.ID, "email")
    password_input = driver.find_element(By.ID, "pass")
    login_button = driver.find_element(By.NAME, "login")

    # FB_EMAIL and FB_PASSWORD are not defined.
    # If you want to use the login function, please define these variables
    # or pass them as arguments to the function.
    # For now, commenting out to avoid errors.
    # email_input.send_keys(FB_EMAIL)
    # password_input.send_keys(FB_PASSWORD)
    
    print(f"{GREEN}Logging in...{RESET}")
    login_button.click()
    time.sleep(10) # Wait for login to complete




def scroll_page_to_load_posts(scroll_count=5):
    """Scrolls the page to load more posts."""
    print(f"{GREEN}[INFO] Start Scrolling (will scroll {scroll_count} times)...{RESET}")
    post_links= set()
    #last_height = driver.execute_script("return document.body.scrollHeight * 0.3")
    #start=0
    
    # for i in tqdm(range(scroll_count)):
    p_height=0
    c_height=0
    i=0
    l=[]
    while(True):
        # Scroll down to bottom
        
        bsh=driver.execute_script(f"window.scrollTo(document.body.scrollHeight * {(i)/50}, document.body.scrollHeight * {(i+2)/50 }); console.log(document.body.scrollHeight); return  document.body.scrollHeight;")
        #start=last_height
        l.append(bsh)
        post_links = extract_post_links(post_links)
        print(f"Found post link: {len(post_links)}")
        # Wait for new posts to load
        i+=1
        if len(l)>=50 and (len(set(l[-50:]))==1):
            print(l[-50:])
            break
            
        time.sleep(1.5)
        
        
    return list(post_links)

def scroll_comments_container(n:int):
    """Scrolls within the comments section to load more comments."""
    print("Scrolling to load all comments...")
    
    # First scroll the main page to ensure comments are visible
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
    time.sleep(2)

    
    current_coord=[]
    previous_coord=None
    
    while current_coord!=previous_coord:
        previous_coord=current_coord
        # Also try scrolling within potential comment containers
        try:
            current_coord=driver.execute_script("""
                var commentContainers = document.querySelectorAll('[role="article"], div[data-testid*="comment"]');
                if (commentContainers.length > 0) {
                    var lastContainer = commentContainers[commentContainers.length - 1];
                    lastContainer.scrollIntoView({behavior: 'smooth', block: 'center'});
                    var rect = lastContainer.getBoundingClientRect();xs
                    return [rect.x, rect.y, rect.width, rect.height];
                }
            """)
        except Exception:
            pass
    
        time.sleep(1.5)

def extract_post_links(post_links:set):
    """Extracts all post links from the current page."""
    print(f"{GREEN}[INFO] Extracting post links...{RESET}")
    
    #post_links = set()  # Use set to avoid duplicates
    
    try:
        # Use JavaScript to find more links
        # js_links = driver.execute_script("""
        #     var links = [];
        #     var allLinks = document.querySelectorAll('a[href]');
            
        #     for (var i = 0; i < allLinks.length; i++) {
        #         var href = allLinks[i].href;
        #         console.log(href)
        #         if (href && (
        #             href.includes('/posts/') && !href.includes('comment_id') || href.includes('/share/p')
        #             )) {
        #             links.push(href);
        #         }
        #     }
            
        #     return [...new Set(links)]; // Remove duplicates
        # """)

        # js_links = driver.execute_script("""
        #     var links = [];
        #     var allLinks = document.querySelectorAll('a[href]');
        #     var debugInfo = {
        #         totalLinks: allLinks.length,
        #         patterns: {},
        #         foundLinks: []
        #     };
            
        #     console.log('Total links found:', allLinks.length);
            
        #     for (var i = 0; i < allLinks.length; i++) {
        #         var href = allLinks[i].href;
                
        #         // Debug: Track different URL patterns
        #         if (href) {
        #             if (href.includes('/posts/')) debugInfo.patterns.posts = (debugInfo.patterns.posts || 0) + 1;
        #             if (href.includes('/share/p/')) debugInfo.patterns.shareP = (debugInfo.patterns.shareP || 0) + 1;
        #             if (href.includes('story_fbid')) debugInfo.patterns.storyFbid = (debugInfo.patterns.storyFbid || 0) + 1;
        #             if (href.includes('/permalink/')) debugInfo.patterns.permalink = (debugInfo.patterns.permalink || 0) + 1;
        #             if (href.includes('/photo/')) debugInfo.patterns.photo = (debugInfo.patterns.photo || 0) + 1;
        #             if (href.includes('/videos/')) debugInfo.patterns.videos = (debugInfo.patterns.videos || 0) + 1;
        #         }
                
        #         // Updated patterns for current Facebook URLs
        #         if (href && (
        #             // Standard post URLs
        #             (href.includes('/posts/') && !href.includes('comment_id') && !href.includes('reply_comment_id')) ||
        #             // Share URLs
        #             href.includes('/share/p/') ||
        #             // Story URLs
        #             href.includes('story_fbid=') ||
        #             // Permalink URLs
        #             href.includes('/permalink/') ||
        #             // Photo URLs that are posts
        #             (href.includes('/photo/') && !href.includes('comment_id')) ||
        #             // Video URLs that are posts
        #             (href.includes('/videos/') && !href.includes('comment_id')) ||
        #             // New Facebook URL patterns
        #             href.match(/facebook\\.com\\/[^\/]+\\/posts\\/\\d+/) ||
        #             // Reel URLs
        #             href.includes('/reel/')
        #         )) {
        #             links.push(href);
        #             debugInfo.foundLinks.push(href);
        #             console.log('Found post URL:', href);
        #         }
        #     }
            
        #     console.log('Debug info:', debugInfo);
        #     return {
        #         links: [...new Set(links)],
        #         debug: debugInfo
        #     };
        # """)
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
                if (!href || !href.includes("facebook.com") || !href.includes("jafiklblan20")) continue;

                for (const regex of postRegexes) {
                    if (regex.test(href)) {
                        links.add(href.split('?')[0]); // strip tracking
                        break;
                    }
                }
            }

            return Array.from(links);
        """

        
        js_links = driver.execute_script(js_script)
        print(js_links)
        
        for link in js_links:
            if is_valid_post_link(link):
                clean_url = clean_facebook_url(link)
                post_links.add(clean_url)
    except Exception as e:
        print(f"{RED}[Error] extracting post links: {e}{RESET}")
    return post_links

def is_valid_post_link(url):
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

def clean_facebook_url(url):
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

def scrape_page_post_links(page_url, scroll_count=5):
    """Main function to scrape post links from a Facebook page."""
    print(f"{GREEN}[INFO] Navigating to page: {page_url}{RESET}")
    driver.get(page_url)
    time.sleep(6)
    # Scroll to load more posts
    post_links= scroll_page_to_load_posts(scroll_count) #scroll_comments_container(None)
    print(f"{GREEN}[INFO] End of scrolling{RESET}")
    # Extract post links
    print(f"{GREEN}[INFO] Start extract post links...{RESET}")
    post_links= set()
    post_links = extract_post_links(post_links)
    print(f"{GREEN}[INFO] End extract post links...{RESET}")
    return post_links

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    try:
        # Temporarily commenting out login() due to undefined FB_EMAIL/FB_PASSWORD
        # login()
        post_links = scrape_page_post_links(PAGE_URL, scroll_count=10)
        
        # Save results
        results = {
            "page_url": PAGE_URL,
            "total_posts_found": len(post_links),
            "post_links": list(post_links),
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        print(results)
        with open("facebook_post_links.json", "w", encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n{GREEN}[INFO] Scraping complete!{RESET}")
        print(f"{GREEN}[INFO] Found {len(post_links)} unique post links{RESET}")
        print(f"{GREEN}[INFO] Results saved to: facebook_post_links.json{RESET}")
        
        
    except Exception as e:
        print(f"{RED}[ERROR] An error occurred: {e}{RESET}")
    finally:
        driver.quit()