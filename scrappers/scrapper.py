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

from utils import open_chrome
#from links import scrape_page_post_links


PAGE_URL = "https://www.facebook.com/jafiklblan20"
POST_URL = "https://www.facebook.com/ridouane.erramdani/posts/pfbid02bqZ7zNPZNpJsn69BgGrWsmUx8cfLBeYfTzE4UJYpyhGog88hzykBHRWof7qQb9jhl"

# --- SETUP THE BROWSER ---
def setup_browser(head_mode=False):
    chrome_options = Options()
    # This option disables browser notifications (e.g., "Chrome is being controlled by automated test software")
    chrome_options.add_argument("--disable-notifications")
    # Optional: run in headless mode (no GUI)
    if head_mode:
        chrome_options.add_argument("--headless")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    print("Setting up WebDriver...")
    # # Use webdriver-manager to automatically handle the driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10) # Implicit wait for elements to appear

    print("Setting up WebDriver...")
    #service = Service(ChromeDriverManager().install())
    #driver = webdriver.Chrome(service=service, options=chrome_options)
    #wait = WebDriverWait(driver, 20)
    return driver
driver = open_chrome()

# def login():
#     """Logs into Facebook."""
#     print("Navigating to Facebook login page...")
#     driver.get("https://www.facebook.com")

#     # Handle cookie consent button if it appears
#     try:
#         # The button might have different data-testid values, check the one on your page
#         cookie_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='cookie-policy-manage-dialog-accept-button']")
#         print("Accepting cookies...")
#         cookie_button.click()
#         time.sleep(1)
#     except NoSuchElementException:
#         print("Cookie consent button not found, continuing...")

#     print("Entering credentials...")
#     email_input = driver.find_element(By.ID, "email")
#     password_input = driver.find_element(By.ID, "pass")
#     login_button = driver.find_element(By.NAME, "login")

#     email_input.send_keys(FB_EMAIL)
#     password_input.send_keys(FB_PASSWORD)
    
#     print("Logging in...")
#     login_button.click()
#     time.sleep(5) # Wait for login to complete


def get_comment_count():
    """Extracts the total comment count displayed by Facebook."""
    print("Extracting comment count from post...")
    
    comment_count = 0
    comment_count_text = ""
    
    try:
        # Use JavaScript to find comment count more reliably
        comment_count_script = """
        // Look for elements containing comment-related text
        var elements = document.querySelectorAll('span, a, div');
        var commentTexts = [];
        
        for (var i = 0; i < elements.length; i++) {
            var text = elements[i].textContent || elements[i].innerText;
            if (text) {
                var lowerText = text.toLowerCase();
                // English patterns
                if (lowerText.includes('comments') && (
                    lowerText.match(/\\d+.*comments/) || 
                    lowerText.match(/comments.*\\d+/) ||
                    lowerText.includes('comments')
                )) {
                    commentTexts.push({text: text, element: elements[i]});
                }
                // Arabic patterns (تعليق = comment in Arabic)
                if (text.includes('تعليق') && text.match(/\\d+/)) {
                    commentTexts.push({text: text, element: elements[i]});
                }
            }
        }
        
        return commentTexts.map(item => item.text);
        """
        
        comment_texts = driver.execute_script(comment_count_script)
        # For each comment_texts element, print out the mapping "number comments" if it matches the pattern
        import re
        for text in comment_texts:
            match = re.match(r"(\d+)\s*comments", text.lower())
            if match:
                comment_count = int(match.group(1))
                break
    except Exception as e:
        print(f"Error extracting comment count: {e}")
    
    return comment_count

def scroll_comments_container(n:int):
    """Scrolls within the comments section to load more comments."""
    print("Scrolling to load all comments...")
    current_coord=[]
    previous_coord=None
    comments=set()
    while current_coord!=previous_coord:
        previous_coord=current_coord
        # Also try scrolling within potential comment containers
        try:
            current_coord=driver.execute_script("""
                var commentContainers = document.querySelectorAll('[role="article"], div[data-testid*="comment"]');
                if (commentContainers.length > 0) {
                    var lastContainer = commentContainers[commentContainers.length - 1];
                    lastContainer.scrollIntoView({behavior: 'smooth', block: 'center'});
                    var rect = lastContainer.getBoundingClientRect();
                    return [rect.x, rect.y, rect.width, rect.height];
                }
            """)
        except Exception as e:
            print(e)
            pass
        time.sleep(2)
    return comments


def scrape_replies(parent_comment_element):
    """Scrapes replies for a given parent comment element."""
    replies_data = []
    print("  Attempting to scrape replies...")
    try:
        # Refined XPath for reply elements: look for elements with role='article' within the parent comment.
        # This assumes replies are also marked as article roles.
        reply_elements = parent_comment_element.find_elements(By.XPATH, ".//div[@role='article']")
        print(f"  Found {len(reply_elements)} potential reply elements.")

        for reply_element in reply_elements:
            try:
                # Extracting commenter name and comment text for replies
                # The author's name is in a span with 'x193iq5w' and 'dir="auto"'
                reply_author_element = reply_element.find_element(By.XPATH, ".//span[contains(@class, 'x193iq5w') and @dir='auto']")
                # The reply text is in a div with 'dir="auto"' and specific style attributes
                reply_text_element = reply_element.find_element(By.XPATH, ".//div[@dir='auto' and (contains(@style,'text-align: start;') or not(@style))]")

                reply_author = reply_author_element.text
                reply_text = reply_text_element.get_attribute('innerText')

                if reply_author and reply_text:
                    replies_data.append({
                        "author": reply_author,
                        "text": reply_text
                    })
                    print(f"    Reply Author: {reply_author}\n    Reply: {reply_text}\n    ---")
            except NoSuchElementException as e:
                print(f"    Could not extract author or text for a reply due to: {e}. Skipping this reply.")
                # For deeper debugging, uncomment the line below to print the HTML of the failing reply element:
                # print(f"    Failed reply HTML:\n{reply_element.get_attribute('outerHTML')}")
                continue
    except Exception as e:
        print(f"  Error while trying to find reply elements: {e}")
    return replies_data


def scrap_comments():
    comments_data = []
    print("\n--- COMMENTS ---")
    try:
        comment_elements = driver.find_elements(By.XPATH, "//div[@role='article']")
        print(f"[INFO] number of comments {len(comment_elements)}")
        for i, comment in enumerate(tqdm(comment_elements)):
            if i==0:
                continue
            try:
                comment_text_elements = comment.find_elements(By.XPATH, ".//div[@dir='auto' and (contains(@style,'text-align: start;') or not(@style))]") 

                #commenter_name = commenter_name_element.text
                comment_text = [comment_text_element.get_attribute('innerText') for comment_text_element in comment_text_elements ]
                # Filter out empty or irrelevant tex
                if comment_text:
                    comment= " ".join(comment_text)
                    comments_data.append(comment)

            except NoSuchElementException as e:
                print(f"[{i}] Could not extract commenter name or text for a comment due to: {e}. Skipping this comment.")
                continue
    except NoSuchElementException:
        print("Could not find comment elements. Selectors might be outdated.")
    print(len(comments_data))
    return comments_data

def scrap_main_post():
    post_text = ""
    try:
        post_element = driver.find_element(By.CSS_SELECTOR, "div[data-ad-preview='message']")
        post_text = post_element.text
    except NoSuchElementException:
        print("Could not find the main post text element. Selector might be outdated.")
    return post_text


def scrape_post_and_comments():
    """Navigates to the post, scrolls to load comments, and scrapes data."""
    print(f"Navigating to post: {POST_URL}")
    driver.get(POST_URL)
    time.sleep(5) # Allow page to load

    # --- SCROLL TO LOAD COMMENTS ---
    post_text = scrap_main_post()
    scroll_comments_container(10)
    comments=scrap_comments()
    # --- SCRAPE THE MAIN POST ---

    # # --- SCRAPE THE COMMENTS ---
    # comments_data = []
    # print("\n--- COMMENTS ---")
    # try:
    #     # This selector targets comment blocks. It is also FRAGILE.
    #     comment_elements = driver.find_elements(By.XPATH, "//div[@role='article']")
    #     print(f"[INFO] number of comments {len(comment_elements)}")
    #     for i, comment in enumerate(tqdm(comment_elements)):
    #         if i==0:
    #             continue
    #         try:
    #             # Extracting commenter name and comment text
    #             # These child selectors are also extremely fragile
    #             #commenter_name_element = comment.find_element(By.XPATH, ".//span[contains(@class, 'x193iq5w') and @dir='auto']")
    #             comment_text_elements = comment.find_elements(By.XPATH, ".//div[@dir='auto' and (contains(@style,'text-align: start;') or not(@style))]") 

    #             #commenter_name = commenter_name_element.text
    #             comment_text = [comment_text_element.get_attribute('innerText') for comment_text_element in comment_text_elements ]
    #             # Filter out empty or irrelevant text
    #             comment_info=None
    #             if comment_text:
    #                 comment_info = {
    #                     "text": " ".join(comment_text),
    #                     "replies": [] # Initialize replies list for this comment
    #                 }
                    
    #                 #print(f"Author: {commenter_name}\nComment: {comment_text}\n---")

    #         except NoSuchElementException as e:
    #             print(f"[{i}] Could not extract commenter name or text for a comment due to: {e}. Skipping this comment.")
    #             # You might want to print more info here, e.g., the outerHTML of the 'comment' element:
    #             # print(f"Failed comment HTML:\n{comment.get_attribute('outerHTML')}")
    #             continue
    
            
            
    #         if comment_info:
    #             comments_data.append(comment_info)
    # except NoSuchElementException:
    #     print("Could not find comment elements. Selectors might be outdated.")
    
    return {"post_text": post_text, "comments": list(set(comments))}


# --- MAIN EXECUTION ---
if __name__ == "__main__":

        #post_links=scrape_page_post_links(page_url=PAGE_URL)
        data={}
        # for i,pl in enumerate(post_links):
        #     print("[INFO] scrap post {i+1} ...")
        #     POST_URL= pl
        scraped_data = scrape_post_and_comments()
        #     data[f"post_{i+1}"]=scraped_data
        with open("comments.json","w") as f:
            f.write(json.dumps(scraped_data, ensure_ascii=False, indent=2))
        
        print("[INFO] Scraping complete.")
        driver.quit()