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

# Change this to the Facebook page you want to scrape
PAGE_URL = "https://www.facebook.com/jafiklblan20"

# --- SETUP THE BROWSER ---
chrome_options = Options()
chrome_options.add_argument("--disable-notifications")
# Optional: run in headless mode (no GUI)
# chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

print("Setting up WebDriver...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.implicitly_wait(10)
wait = WebDriverWait(driver, 20)
FB_EMAIL=""
FB_PASSWORD=""

def login():
    """Logs into Facebook."""
    print("Navigating to Facebook login page...")
    driver.get("https://www.facebook.com")

    # Handle cookie consent button if it appears
    try:
        # The button might have different data-testid values, check the one on your page
        cookie_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='cookie-policy-manage-dialog-accept-button']")
        print("Accepting cookies...")
        cookie_button.click()
        time.sleep(1)
    except NoSuchElementException:
        print("Cookie consent button not found, continuing...")

    print("Entering credentials...")
    email_input = driver.find_element(By.ID, "email")
    password_input = driver.find_element(By.ID, "pass")
    login_button = driver.find_element(By.NAME, "login")

    email_input.send_keys(FB_EMAIL)
    password_input.send_keys(FB_PASSWORD)
    
    print("Logging in...")
    login_button.click()
    time.sleep(10) # Wait for login to complete

def scroll_page_to_load_posts(scroll_count=5):
    """Scrolls the page to load more posts."""
    print(f"Scrolling page to load posts (will scroll {scroll_count} times)...")
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    for i in range(scroll_count):
        print(f"Scroll {i+1}/{scroll_count}")
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for new posts to load
        time.sleep(1.5)
        
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("No more content to load")
            break
        last_height = new_height

def extract_post_links():
    """Extracts all post links from the current page."""
    print("Extracting post links...")
    
    post_links = set()  # Use set to avoid duplicates
    
    try:
        # Method 1: Look for article elements (posts are usually wrapped in article tags)
        post_elements = driver.find_elements(By.XPATH, "//div[@role='article']")
        print(f"Found {len(post_elements)} article elements")
        
        for post_element in post_elements:
            try:
                # Look for links within each post that lead to the post itself
                # These are usually timestamp links or "View full post" links
                link_elements = post_element.find_elements(By.XPATH, ".//a[contains(@href, '/posts/') or contains(@href, '/share/p/') or contains(@href, 'story_fbid')]")
                
                for link_element in link_elements:
                    href = link_element.get_attribute('href')
                    if href and is_valid_post_link(href):
                        # Clean the URL (remove tracking parameters)
                        clean_url = clean_facebook_url(href)
                        post_links.add(clean_url)
                        print(f"Found post link: {clean_url}")
                        
            except Exception as e:
                print(f"Error processing post element: {e}")
                continue
        
        # Method 2: Use JavaScript to find more links
        print("Using JavaScript to find additional post links...")
        js_links = driver.execute_script("""
            var links = [];
            var allLinks = document.querySelectorAll('a[href]');
            
            for (var i = 0; i < allLinks.length; i++) {
                var href = allLinks[i].href;
                if (href && (
                    href.includes('/posts/') || 
                    href.includes('/share/p/') || 
                    href.includes('story_fbid') ||
                    href.includes('/permalink/')
                )) {
                    links.push(href);
                }
            }
            
            return [...new Set(links)]; // Remove duplicates
        """)
        
        for link in js_links:
            if is_valid_post_link(link):
                clean_url = clean_facebook_url(link)
                post_links.add(clean_url)
                
    except Exception as e:
        print(f"Error extracting post links: {e}")
    
    return list(post_links)

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
    except:
        return url

def scrape_page_post_links(page_url, scroll_count=5):
    """Main function to scrape post links from a Facebook page."""
    print(f"Navigating to page: {page_url}")
    login()
    driver.get(page_url)
    time.sleep(5)  # Allow page to load
    
    # Handle any cookie consent dialogs
    try:
        cookie_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='cookie-policy-manage-dialog-accept-button']")
        print("Accepting cookies...")
        cookie_button.click()
        time.sleep(2)
    except NoSuchElementException:
        print("No cookie consent dialog found")
    
    # Scroll to load more posts
    scroll_page_to_load_posts(scroll_count)
    
    # Extract post links
    post_links = extract_post_links()
    
    return post_links

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    try:
        post_links = scrape_page_post_links(PAGE_URL, scroll_count=10)
        
        # Save results
        results = {
            "page_url": PAGE_URL,
            "total_posts_found": len(post_links),
            "post_links": post_links,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open("facebook_post_links.json", "w", encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\nScraping complete!")
        print(f"Found {len(post_links)} unique post links")
        print("Results saved to: facebook_post_links.json")
        
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()