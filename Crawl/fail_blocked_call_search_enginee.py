import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from urllib.parse import urljoin, urlparse
from markdownify import markdownify as md
import re

# --- Configuration ---
SEARCH_QUERY = "what is deepmind?"
MAX_SEARCH_RESULTS_TO_CLICK = 3 # Limiting for demonstration, adjust as needed
MAX_PAGES_PER_LINK = 2 # Limiting for demonstration, adjust as needed

# User-Agent to make requests appear more like a regular browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

# --- 1. & 2. Perform Search and Get Links ---
# Using requests to try and scrape DuckDuckGo.
# This is a basic attempt and highly prone to being blocked.
# For robust solutions, use paid APIs (SerpApi, Oxylabs, etc.) or self-host SearxNG.
def search_duckduckgo(query):
    search_url = f"https://duckduckgo.com/html/?q={query}"
    print(f"Searching DuckDuckGo for: {query}")
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'html.parser')

        # DuckDuckGo's HTML structure might change. This is based on typical patterns.
        # Look for links within results.
        results = []
        for a_tag in soup.find_all('a', class_='result__url'):
            link = a_tag.get('href')
            if link and link.startswith('http'):
                results.append(link)
        
        # If the above doesn't work, try other common result selectors like 'result__a' or a parent div
        if not results:
            for link_div in soup.find_all('div', class_='result__body'):
                link_tag = link_div.find('a', class_='result__a')
                if link_tag and link_tag.get('href') and link_tag.get('href').startswith('http'):
                    results.append(link_tag.get('href'))


        return results
    except requests.exceptions.RequestException as e:
        print(f"Error searching DuckDuckGo: {e}")
        print("DuckDuckGo scraping is often blocked. Consider using a dedicated SERP API or trying again later.")
        return []

# --- Helper to get domain for restricting navigation ---
def get_domain(url):
    return urlparse(url).netloc

# --- 3. Automate Clicking and Navigation ---
def automate_and_extract(search_links):
    all_extracted_content = {}

    chrome_options = Options()
    # Uncomment the line below to run headless (no browser window will open)
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu") # Recommended for headless on some systems
    chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")

    # Use webdriver_manager to automatically download and manage ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Maximize window for better rendering/finding elements (less relevant for headless)
    driver.maximize_window()

    visited_urls = set() # To avoid infinite loops or re-visiting

    for i, link in enumerate(search_links[:MAX_SEARCH_RESULTS_TO_CLICK]):
        print(f"\n--- Processing Search Result {i+1}: {link} ---")
        current_domain = get_domain(link)
        current_link_content = []
        
        try:
            driver.get(link)
            time.sleep(2) # Give page time to load
            
            page_count = 0
            while page_count < MAX_PAGES_PER_LINK:
                current_url = driver.current_url
                if current_url in visited_urls:
                    print(f"Already visited {current_url}. Skipping.")
                    break
                visited_urls.add(current_url)

                print(f"Navigating to: {current_url} (Page {page_count+1})")
                
                # --- 4. Read Raw HTML and Convert to Markdown ---
                raw_html = driver.page_source
                markdown_content = convert_html_to_markdown(raw_html, current_url)
                
                current_link_content.append({
                    "url": current_url,
                    "markdown_content": markdown_content
                })
                
                # Attempt to find "next" page link (this is highly generalized and may fail)
                # This is the trickiest part for generic navigation.
                next_page_link = None
                try:
                    # Common selectors for "next" buttons/links
                    # Prioritize links within the same domain and not external
                    potential_next_links = driver.find_elements(
                        by=webdriver.common.by.By.XPATH,
                        value="//a[contains(text(),'next') or contains(text(),'Next') or @rel='next' or @class='next']"
                    )
                    for next_link_element in potential_next_links:
                        href = next_link_element.get_attribute('href')
                        if href and urljoin(current_url, href).startswith(f"https://{current_domain}") and urljoin(current_url, href) != current_url:
                            next_page_link = href
                            break
                    
                    if next_page_link:
                        # Before clicking, check if we've already visited to prevent loops
                        absolute_next_url = urljoin(current_url, next_page_link)
                        if absolute_next_url in visited_urls:
                            print(f"Next page link {absolute_next_url} already visited. Stopping navigation for this result.")
                            break
                        
                        print(f"Found next page link: {absolute_next_url}")
                        driver.get(absolute_next_url)
                        time.sleep(2) # Wait for the new page to load
                    else:
                        print("No 'next' page link found for this domain. Stopping navigation.")
                        break # No more pages to navigate within this link
                except Exception as e:
                    print(f"Error finding/clicking next page link: {e}")
                    break # Stop if an error occurs

                page_count += 1
                if not next_page_link: # If no next link was found, stop
                    break
                    
        except Exception as e:
            print(f"Error processing {link}: {e}")
        
        all_extracted_content[link] = current_link_content

    driver.quit()
    return all_extracted_content

# --- 4. Python code that read the raw html and return as markdown ---
def convert_html_to_markdown(html_content, base_url):
    """
    Converts raw HTML content to Markdown, including text, image blocks, and hyperlinks.
    Handles relative links by converting them to absolute URLs.
    """
    
    # Use markdownify to convert HTML to Markdown
    # We'll use a custom converter for images to ensure full URLs if they are relative
    
    class CustomMarkdownConverter(md.MarkdownConverter):
        def convert_img(self, el, text, parent_tags):
            src = el.get('src')
            alt = el.get('alt', '')
            if src:
                # Resolve relative URLs
                absolute_src = urljoin(base_url, src)
                return f"![{alt}]({absolute_src})\n\n" # Add newlines for block-like behavior
            return ""

        def convert_a(self, el, text, parent_tags):
            href = el.get('href')
            if href:
                absolute_href = urljoin(base_url, href)
                return f"[{text}]({absolute_href})"
            return text # If no href, just return the text

    converter = CustomMarkdownConverter(
        strong_em_symbol='**',  # Use ** for bold
        bullets='*',            # Use * for list items
        code_language='python'  # Default for code blocks if no language specified
    )
    
    markdown_output = converter.convert(html_content)

    # Further cleanup or specific formatting adjustments for LLM can be done here
    # For example, removing excessive whitespace or specific boilerplate text
    markdown_output = re.sub(r'\n\s*\n', '\n\n', markdown_output) # Remove multiple blank lines
    markdown_output = re.sub(r'\[]\(([^)]+)\)', r'(\1)', markdown_output) # Convert empty link text to just the URL in parentheses
    
    return markdown_output

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Search query: \"{SEARCH_QUERY}\"")
    
    # Step 1 & 2: Get search results
    search_links = search_duckduckgo(SEARCH_QUERY)
    
    if not search_links:
        print("No search results found or search was blocked. Exiting.")
    else:
        print(f"\nFound {len(search_links)} search results. Processing top {min(MAX_SEARCH_RESULTS_TO_CLICK, len(search_links))} links.")
        
        # Step 3 & 4: Automate clicks, navigate, and extract content
        extracted_data = automate_and_extract(search_links)

        # Print all extracted content
        print("\n--- Extracted Content Summary ---")
        for original_link, pages_content in extracted_data.items():
            if pages_content:
                print(f"\nOriginal Link: {original_link}")
                for page_num, page_data in enumerate(pages_content):
                    print(f"  Page {page_num + 1} URL: {page_data['url']}")
                    print("  --- Markdown Content (Excerpt) ---")
                    # Print first 500 characters or less
                    print(page_data['markdown_content'][:500] + ("..." if len(page_data['markdown_content']) > 500 else ""))
                    print("  ---------------------------------")
            else:
                print(f"\nNo content extracted for {original_link}")

        # You can now process `extracted_data` with your LLM.
        # For example, save it to JSON files:
        # import json
        # with open("extracted_search_data.json", "w", encoding="utf-8") as f:
        #     json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        # print("\nExtracted data saved to extracted_search_data.json")