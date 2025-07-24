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


POST_URL = "https://www.facebook.com/share/p/177bf2KtUw/" 

# --- SETUP THE BROWSER ---
chrome_options = Options()
# This option disables browser notifications (e.g., "Chrome is being controlled by automated test software")
chrome_options.add_argument("--disable-notifications")
# Optional: run in headless mode (no GUI)
# chrome_options.add_argument("--headless")

# print("Setting up WebDriver...")
# # Use webdriver-manager to automatically handle the driver
# service = Service(ChromeDriverManager().install())
# driver = webdriver.Chrome(service=service, options=chrome_options)
# driver.implicitly_wait(10) # Implicit wait for elements to appear

print("Setting up WebDriver...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 20)

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

def scroll_comments_container():
    """Scrolls within the comments section to load more comments."""
    print("Scrolling to load all comments...")
    
    # First scroll the main page to ensure comments are visible
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
    time.sleep(2)
    
    # Try to find and scroll within the comments container
    scroll_attempts = 0
    current_comments=0
    previous_comments=-1
    while current_comments!=previous_comments:
        previous_comments=current_comments
        # Scroll down gradually
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(3)
        
        # Also try scrolling within potential comment containers
        try:
            driver.execute_script("""
                var commentContainers = document.querySelectorAll('[role="article"], div[data-testid*="comment"]');
                if (commentContainers.length > 0) {
                    var lastContainer = commentContainers[commentContainers.length - 1];
                    lastContainer.scrollIntoView({behavior: 'smooth', block: 'center'});
                }
            """)
        except Exception:
            pass
        
        time.sleep(1)
        
        scroll_attempts+=1
        
        # Press Page Down key occasionally to trigger lazy loading
        if scroll_attempts % 5 == 0:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
            time.sleep(1)
        comment_elements = driver.find_elements(By.XPATH, "//div[@role='article']")
        current_comments=len(comment_elements)
    print(f"[INFO] Found {current_comments}")


def scrape_post_and_comments():
    """Navigates to the post, scrolls to load comments, and scrapes data."""
    print(f"Navigating to post: {POST_URL}")
    driver.get(POST_URL)
    time.sleep(5) # Allow page to load

    # --- SCROLL TO LOAD COMMENTS ---
    scroll_comments_container()
    # --- SCRAPE THE MAIN POST ---
    post_text = ""
    try:
        # This selector is very fragile and WILL change.
        # You need to inspect the page to find the correct one.
        post_element = driver.find_element(By.CSS_SELECTOR, "div[data-ad-preview='message']")
        post_text = post_element.text
        print("\n--- POST ---")
        print(post_text)
    except NoSuchElementException:
        print("Could not find the main post text element. Selector might be outdated.")

    # --- SCRAPE THE COMMENTS ---
    comments_data = []
    print("\n--- COMMENTS ---")
    try:
        # This selector targets comment blocks. It is also FRAGILE.
        comment_elements = driver.find_elements(By.XPATH, "//div[@role='article']")
        print(f"[INFO] number of comments {len(comment_elements)}")
        for i, comment in enumerate(tqdm(comment_elements)):
            try:
                # Extracting commenter name and comment text
                # These child selectors are also extremely fragile
                commenter_name_element = comment.find_element(By.XPATH, ".//span[contains(@class, 'x193iq5w') and @dir='auto']")
                comment_text_element = comment.find_element(By.XPATH, ".//div[@dir='auto' and (contains(@style,'text-align: start;') or not(@style))]") 

                commenter_name = commenter_name_element.text
                comment_text = comment_text_element.get_attribute('innerText') # Use innerText for potentially better handling of nested elements like emojis

                # Filter out empty or irrelevant text
                if commenter_name and comment_text:
                    comments_data.append({
                        "author": commenter_name,
                        "text": comment_text
                    })
                    print(f"Author: {commenter_name}\nComment: {comment_text}\n---")

            except NoSuchElementException as e:
                print(f"[{i}] Could not extract commenter name or text for a comment due to: {e}. Skipping this comment.")
                # You might want to print more info here, e.g., the outerHTML of the 'comment' element:
                # print(f"Failed comment HTML:\n{comment.get_attribute('outerHTML')}")
                continue
                
    except NoSuchElementException:
        print("Could not find comment elements. Selectors might be outdated.")
    
    return {"post_text": post_text, "comments": comments_data}


# --- MAIN EXECUTION ---
if __name__ == "__main__":
        scraped_data = scrape_post_and_comments()
        with open("comments.json","w") as f:
            f.write(json.dumps(scraped_data, ensure_ascii=False, indent=2))
        
        print(f"\nScraping complete. Found {len(scraped_data['comments'])} comments.")
        driver.quit()