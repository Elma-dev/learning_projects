
import time
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from tqdm import tqdm
import json

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

class FacebookPostScraper():
    def __init__(self):
        self.driver=self.open_chrome()
        self.comments=[]
        self.post_text=""
        pass

    def open_chrome(self):
        chrome_options= webdriver.ChromeOptions()
        chrome_options.debugger_address= "localhost:9222"
        return webdriver.Chrome(options=chrome_options)

    def scroll_comments_container(self):
        """Scrolls within the comments section to load more comments."""
        current_coord=[]
        previous_coord=None
        while current_coord!=previous_coord:
            previous_coord=current_coord
            try:
                current_coord=self.driver.execute_script("""
                    var commentContainers = document.querySelectorAll('[role="article"], div[data-testid*="comment"]');
                    if (commentContainers.length > 0) {
                        var lastContainer = commentContainers[commentContainers.length - 1];
                        lastContainer.scrollIntoView({behavior: 'smooth', block: 'center'});
                        var rect = lastContainer.getBoundingClientRect();
                        return [rect.x, rect.y, rect.width, rect.height];
                    }
                """)
            except Exception as e:
                print(f"{RED}[Error]: {e}{RESET}")
                pass
            time.sleep(2)
    
    def scrap_comments(self):
        try:
            comment_elements = self.driver.find_elements(By.XPATH, "//div[@role='article']")
            for i, comment in enumerate(tqdm(comment_elements)):
                if i==0:
                    continue
                try:
                    comment_text_elements = comment.find_elements(By.XPATH, ".//div[@dir='auto' and (contains(@style,'text-align: start;') or not(@style))]") 
                    comment_text = [comment_text_element.get_attribute('innerText') for comment_text_element in comment_text_elements ]
                    # Filter out empty or irrelevant tex
                    if comment_text:
                        comment= " ".join(comment_text)
                        self.comments.append(comment)

                except NoSuchElementException as e:
                    print(f"{RED}[Error]: [{i}] Could not extract commenter name or text for a comment due to: {e}. Skipping this comment.{RESET}")
                    continue
        except NoSuchElementException:
            print("Could not find comment elements. Selectors might be outdated.")
        return self.comments
    
    def scrap_main_post(self):
        try:
            post_element = self.driver.find_element(By.CSS_SELECTOR, "div[data-ad-preview='message']")
            self.post_text = post_element.text
        except NoSuchElementException:
            print(f"{RED}[Error]: Could not find the main post text element. Selector might be outdated.{RESET}")

    def scrape_post_and_comments(self,post_url,to_save=False,save_path="post_comments.json"):
        """Navigates to the post, scrolls to load comments, and scrapes data."""
        print(f"Navigating to post: {post_url}")
        print(f"{GREEN}[INFO]:{RESET} Navigating to post: {post_url}")
        self.driver.get(post_url)
        time.sleep(5) # Allow page to load

        # --- SCROLL TO LOAD COMMENTS ---
        print(f"{GREEN}[INFO]:{RESET} Get Main Post...")
        self.scrap_main_post()
        print(f"{GREEN}[INFO]:{RESET} Scrolling...")
        self.scroll_comments_container()
        print(f"{GREEN}[INFO]:{RESET} Scrap Comments...")
        self.scrap_comments()
        scraped_data = {"post_text": self.post_text, "comments": list(set(self.comments))}
        if to_save:
            print(f"{GREEN}[INFO]:{RESET} Save Result...")
            with open(save_path,"w") as f:
                f.write(json.dumps(scraped_data, ensure_ascii=False, indent=2))
        print(f"{GREEN}[INFO]:{RESET} Encd Of Scrapping")
        return scraped_data


if __name__=="__main__":
    post="https://www.facebook.com/ridouane.erramdani/posts/pfbid02bqZ7zNPZNpJsn69BgGrWsmUx8cfLBeYfTzE4UJYpyhGog88hzykBHRWof7qQb9jhl"
    facebook_post_scraper= FacebookPostScraper()
    facebook_post_scraper.scrape_post_and_comments(post_url=post)