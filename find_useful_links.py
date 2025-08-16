import requests
import os
import re
import random
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

def get_clients():

    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    get_clients.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_api_key, temperature=0, max_retries=2)
    
    # User agents for scraping
    get_clients.user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/117.0 Safari/537.36",
    ]
    # Base headers for scraping
    get_clients.base_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Prompt template for filtering out irrelevant links using LLM
    get_clients.filter_link = """
        You are helping to build a knowledge base focused on insurance related information. The knowledge base must include details
        1. related to insurance products or services
        2. Educational content like FAQs, support articles, or guides and best practices related to covered products/services
        3. Claims process, benefits, eligibility, or how coverage works.
        4. Different locations specific resources or rules and regulations.
        5. Customer resources, how-to use pages, or product knowledge
        6. Offers general lifestyle or buying advice that includes or connects to insurance considerations
        7. Introduces insurance concepts, terminology, or planning for specific life stages

        You have a strong attention to detail in identifying pages that DO NOT contribute useful knowledge. Because most of the links are relevant with only a few that are not useful.

        Given a list of URLs your task is to identify links that are clearly irrelevant to insurance knowledge that need NOT BE SCRAPED for information.
        Be careful to not include any useful page as we want the knowledge base to be thorough! Do not flag a link unless you are sure!

        Examples of NOT useful links are:
        Job listings, career or internship pages
        Executive bios, leadership profiles, investor pages
        Company history, values, or press releases
        Login or portal-only pages (with no public info)

        For each link you identify is not useful, provide:

        "url": the filtered out link
        "reason": short explanation why the page is NOT useful to the insurance knowledge base

        Below is the list of URLs to evaluate:
        {url_links}
        """
    
    return get_clients.llm, get_clients.user_agents, get_clients.base_headers, get_clients.filter_link

def get_links(text: str)->list:
  """
    Extracts all URLs from the given text using a regular expression.
    Returns a list of found links.
    """
  # https_regex = r"https?://[^\s)\"\']+"
  https_regex = r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
  links = re.findall(https_regex, text)
  return links

def scrape_html(url, headers, agents, max_retries=3, timeout=10, sleep_range=(1.5, 4.0)):
    """
    Attempts to scrape HTML content from the given URL using randomized user agents and retry logic.
    Returns the HTML content on success, or None if all retries fail.
    """
    for attempt in range(1, max_retries + 1):
        try:
            headers = headers.copy()
            headers["User-Agent"] = random.choice(agents)
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            print(f"Successfully scraped {url} on attempt {attempt}")
            return response.text

        except requests.exceptions.RequestException as e:
            print(f"Error on attempt {attempt}: {e}")
            if attempt < max_retries:
                sleep_time = random.uniform(*sleep_range)
                print(f"Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            else:
                print("Max retries reached. Skipping.")
                return None


def find_useful_links():
    """
    Main function to process insurance sitemaps:
    - Scrapes sitemap XMLs for links.
    - Uses LLM to filter out irrelevant links.
    - Saves the remaining useful links to a file.
    """
    # Initialize clients
    llm, user_agents, base_headers, filter_link = get_clients()
    sitemap_links = ["https://www.travelers.com/sitemap.xml", "https://www.mercuryinsurance.com/sitemap/sitemap.xml", "https://www.allstate.com/sitemap-main.xml", "https://www.usaa.com/sitemap.xml", ]
    for sitemap_link in sitemap_links:
        cnt += 1
        print(f"Processing sitemap: {sitemap_link}")
        # Scrape the sitemap HTML
        sitemap_html = scrape_html(sitemap_link, base_headers, user_agents)
        links = get_links(sitemap_html)
        filtered_links=[]
        link_prompt_temp = ChatPromptTemplate.from_template(filter_link)
        i=0
        # Process links in batches of 100 for LLM filtering
        while i<len(links):
            ls = links[i:i+100]
            i +=100
            link_prompt = link_prompt_temp.format_messages(url_links=ls)
            result = llm.invoke(link_prompt)
            filtered_links.extend(get_links(result.content))
            

        file_path = "useful_links.txt"
        useful = list(set(links) - set(filtered_links))
        
        # Save useful links to file
        with open(file_path, "a") as file:
            for item in useful:
                file.write(item + "\n")
        

if __name__ == "__main__":
    find_useful_links()
    print("Useful links have been saved to useful_links.txt")