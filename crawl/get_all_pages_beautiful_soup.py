import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random

def simple_crawler(start_url, max_pages=100, delay_min=1, delay_max=3):
    visited_urls = set()
    urls_to_visit = [start_url]
    scraped_data = [] # To store the extracted data

    # Get the base domain to stay within the website
    base_domain = urlparse(start_url).netloc

    while urls_to_visit and len(visited_urls) < max_pages:
        current_url = urls_to_visit.pop(0) # Use pop(0) for BFS, pop() for DFS

        if current_url in visited_urls:
            continue

        print(f"Crawling: {current_url}")
        visited_urls.add(current_url)

        try:
            response = requests.get(current_url, timeout=10)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            soup = BeautifulSoup(response.text, 'html.parser')

            # --- Data Extraction Logic (Customize this) ---
            title = soup.find('title').get_text() if soup.find('title') else 'No Title'
            paragraphs = [p.get_text() for p in soup.find_all('p')]
            scraped_data.append({
                'url': current_url,
                'title': title,
                'paragraphs': paragraphs
            })
            # -----------------------------------------------

            # Find all links on the page
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(current_url, href)
                parsed_full_url = urlparse(full_url)

                # Ensure it's an HTTP/HTTPS link and within the same domain
                if parsed_full_url.scheme in ['http', 'https'] and parsed_full_url.netloc == base_domain:
                    # Normalize URL (remove fragments like #section)
                    normalized_url = parsed_full_url._replace(fragment="").geturl()

                    if normalized_url not in visited_urls and normalized_url not in urls_to_visit:
                        urls_to_visit.append(normalized_url)

        except requests.exceptions.RequestException as e:
            print(f"Error crawling {current_url}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        # Be polite - add a random delay
        time.sleep(random.uniform(delay_min, delay_max))

    return scraped_data

if __name__ == "__main__":
    start_website = "https://www.example.com" # Replace with the website you want to crawl
    data = simple_crawler(start_website, max_pages=50) # Limit for demonstration
    
    # You can then save 'data' to a file (e.g., JSON)
    import json
    with open("scraped_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"\nScraped {len(data)} pages. Data saved to scraped_data.json")