import json
from post_scraper import FacebookPostScraper

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

if __name__=="__main__":
    post_links_path="fpost_links.json"
    with open(post_links_path,"r") as f:
        post_links = json.loads(f.read())["post_links"]
    facebook_post_scraper= FacebookPostScraper()
    for i,pl in enumerate(post_links):
        print(f"{GREEN}[INFO] Scrap Post {i+1} {RESET}")
        result=facebook_post_scraper.scrape_post_and_comments(post_url=pl)
        # {"post_text": self.post_text, "comments": list(set(self.comments))}
        with open("comments.json", "a", encoding="utf-8") as outfile:
            json.dump(result, outfile, ensure_ascii=False)
            outfile.write("\n")

    
