# Okay, let's design a comprehensive Playwright-based web crawler that can get the content of (virtually) all pages on a given website, saving both HTML and Markdown for each.

# This will involve:

#     A starting URL.

#     A queue to manage URLs to visit.

#     A set to keep track of already visited URLs to prevent infinite loops and redundant processing.

#     Strict domain enforcement to ensure we only crawl pages within the target website.

#     Robust link extraction from each page.

#     Filtering of irrelevant links (e.g., external, mailto, file downloads, very deep paths).

#     Rate limiting to be polite to the server and avoid getting blocked.

#     Error handling for page load failures.

#     Configurable limits (max pages, max depth).

import os
import re
import asyncio
import hashlib
from urllib.parse import urljoin, urlparse, urldefrag, parse_qs, urlencode

# Ensure these are installed:
# pip install playwright beautifulsoup4 markdownify
# playwright install

from playwright.async_api import async_playwright, Page, BrowserContext
from markdownify import markdownify as md
from bs4 import BeautifulSoup

# --- Configuration ---
# Base directory for all scraped output
OUTPUT_BASE_DIR = "crawled_website_data"

# --- Crawler Specific Configuration ---
# The starting URL for the crawl
START_URL = "https://www.example.com" # <<< IMPORTANT: Change this to your target website!

# Maximum number of unique pages to crawl (set to None for no limit, but be careful!)
MAX_PAGES_TO_CRAWL = 50

# Delay between page navigations (in seconds) to be polite to the server
CRAWL_DELAY_SECONDS = 1

# Maximum depth for crawling (0 for only the start URL, 1 for start URL and its direct links, etc.)
# Set to None for no depth limit (use with caution on large sites!)
MAX_CRAWL_DEPTH = 2

# Exclude common file extensions from crawling
EXCLUDE_EXTENSIONS = (
    '.pdf', '.zip', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.mp4', '.mp3', '.avi', '.mov',
    '.css', '.js', '.xml', '.json', '.txt', '.csv', '.rss', '.atom'
)

# --- Helper Functions (Reused from previous discussions) ---

def convert_html_to_markdown_for_llm(html_content: str, base_url: str = "") -> str:
    """
    Converts raw HTML content to Markdown, making it suitable for LLMs.
    Handles relative links/images and performs additional cleanup.
    """
    if not html_content:
        return ""

    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        for img in soup.find_all('img', src=True):
            img['src'] = urljoin(base_url, img['src'])
        for a in soup.find_all('a', href=True):
            a['href'] = urljoin(base_url, a['href'])

        converter = md.MarkdownConverter(
            strong_em_symbol='**',
            bullets='*',
            code_language='python',
            strip=['script', 'style', 'header', 'footer', 'nav', 'aside', 'form', 'button', '.sidebar', '#comments']
        )
        markdown_output = converter.convert(str(soup))

        markdown_output = re.sub(r'\n\s*\n', '\n\n', markdown_output).strip()
        markdown_output = re.sub(r'\[]\(([^)]+)\)', r'(\1)', markdown_output)
        markdown_output = re.sub(r'\n\n\n+', '\n\n', markdown_output)
        
        return markdown_output
    except ImportError:
        print("Warning: BeautifulSoup4 or markdownify not installed. Cannot convert HTML to Markdown.")
        return html_content
    except Exception as e:
        print(f"Error converting HTML to Markdown: {e}")
        return html_content

def generate_filename(url: str, suffix: str = "") -> str:
    """Generates a safe filename from a URL using a hash for uniqueness."""
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    parsed = urlparse(url)
    # Use a cleaned version of the path, or just the hash if path is too generic
    path_segment = parsed.path.strip('/').replace('/', '_').replace('.', '_').replace('-', '_')
    if path_segment:
        # Limit length to avoid excessively long filenames
        clean_name = f"{path_segment[:50]}_{url_hash[:8]}"
    else:
        clean_name = url_hash
    return f"{clean_name}{suffix}"

async def extract_content_and_save_with_playwright(page: Page, url: str, output_dir: str) -> tuple[str, str]:
    """
    Navigates Playwright to a URL, extracts HTML, converts to Markdown, and saves both.
    Returns (markdown_content, html_content) or (None, None) if failed.
    """
    html_content = None
    markdown_content = None
    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
        html_content = await page.content()
        markdown_content = convert_html_to_markdown_for_llm(html_content, url)

        # Sanitize domain name for directory
        parsed_url = urlparse(url)
        domain_folder = re.sub(r'[^a-zA-Z0-9_\-.]', '', parsed_url.netloc)
        page_output_dir = os.path.join(output_dir, domain_folder)
        os.makedirs(page_output_dir, exist_ok=True)

        filename_base = generate_filename(url)
        html_filepath = os.path.join(page_output_dir, f"{filename_base}.html")
        md_filepath = os.path.join(page_output_dir, f"{filename_base}.md")

        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"    Saved HTML to: {html_filepath}")

        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"    Saved Markdown to: {md_filepath}")

        return markdown_content, html_content
    except Exception as e:
        print(f"  Playwright failed to load, extract, or save content from {url}: {e}")
        return None, None

# --- NEW: Core Website Crawler Function ---

async def crawl_website(start_url: str, browser_context: BrowserContext, output_dir: str):
    """
    Crawls a website starting from a given URL, extracts content, and saves it.
    """
    print(f"\nStarting website crawl from: {start_url}")
    print(f"Max pages to crawl: {MAX_PAGES_TO_CRAWL if MAX_PAGES_TO_CRAWL else 'No Limit'}")
    print(f"Max crawl depth: {MAX_CRAWL_DEPTH if MAX_CRAWL_DEPTH else 'No Limit'}")
    print(f"Delay between pages: {CRAWL_DELAY_SECONDS} seconds")

    # Normalize the start URL to get the base domain
    parsed_start_url = urlparse(start_url)
    base_domain = f"{parsed_start_url.scheme}://{parsed_start_url.netloc}"
    
    # Queue for URLs to visit (stores tuples of (url, depth))
    to_visit_queue = asyncio.Queue()
    await to_visit_queue.put((start_url, 0)) # Start with depth 0

    # Set to keep track of visited URLs (normalized to avoid duplicates)
    visited_urls = set()
    
    # List to store all collected content for final LLM input
    all_collected_content = []
    
    # Counter for crawled pages
    crawled_count = 0

    while not to_visit_queue.empty() and (MAX_PAGES_TO_CRAWL is None or crawled_count < MAX_PAGES_TO_CRAWL):
        current_url, current_depth = await to_visit_queue.get()

        # Normalize URL for visited check: remove fragment and sort query params
        normalized_url, _ = urldefrag(current_url)
        parsed_normalized_url = urlparse(normalized_url)
        query_params = parse_qs(parsed_normalized_url.query)
        # Sort query parameters to treat URLs with same params but different order as identical
        sorted_query = urlencode(sorted(query_params.items()), doseq=True)
        normalized_url = parsed_normalized_url._replace(query=sorted_query).geturl()

        if normalized_url in visited_urls:
            print(f"  Skipping already visited: {current_url}")
            continue

        if MAX_CRAWL_DEPTH is not None and current_depth > MAX_CRAWL_DEPTH:
            print(f"  Skipping due to max depth reached ({current_depth}): {current_url}")
            continue

        # Add to visited set
        visited_urls.add(normalized_url)
        crawled_count += 1

        print(f"  Crawling ({crawled_count}/{MAX_PAGES_TO_CRAWL if MAX_PAGES_TO_CRAWL else '∞'}, Depth: {current_depth}): {current_url}")

        page = await browser_context.new_page()
        markdown_content, html_content = await extract_content_and_save_with_playwright(page, current_url, output_dir)
        
        if markdown_content:
            all_collected_content.append({
                "title": await page.title() if page.is_closed() == False else "No Title", # Get title if page is still open
                "url": current_url,
                "markdown_content": markdown_content,
                "html_content": html_content
            })

            # Extract new links for further crawling if within depth limit
            if MAX_CRAWL_DEPTH is None or current_depth < MAX_CRAWL_DEPTH:
                try:
                    link_elements = await page.locator("a").all()
                    for link_element in link_elements:
                        href = await link_element.get_attribute("href")
                        if href:
                            absolute_url = urljoin(current_url, href)
                            parsed_absolute_url = urlparse(absolute_url)

                            # Filter links:
                            # 1. Must be HTTP/HTTPS
                            # 2. Must be within the same base domain
                            # 3. Must not be a common file extension
                            # 4. Must not be a fragment link on the same page
                            if parsed_absolute_url.scheme in ('http', 'https') and \
                               parsed_absolute_url.netloc == parsed_start_url.netloc and \
                               not any(absolute_url.lower().endswith(ext) for ext in EXCLUDE_EXTENSIONS) and \
                               urldefrag(absolute_url)[0] != urldefrag(current_url)[0]: # Avoid same-page fragment links
                                
                                # Normalize potential new URL for visited check
                                new_normalized_url, _ = urldefrag(absolute_url)
                                new_parsed_normalized_url = urlparse(new_normalized_url)
                                new_query_params = parse_qs(new_parsed_normalized_url.query)
                                new_sorted_query = urlencode(sorted(new_query_params.items()), doseq=True)
                                new_normalized_url = new_parsed_normalized_url._replace(query=new_sorted_query).geturl()

                                if new_normalized_url not in visited_urls:
                                    await to_visit_queue.put((absolute_url, current_depth + 1))
                                    # Add to visited set immediately to prevent other tasks from adding it
                                    # (though main visited_urls check handles this for processing)
                                    # visited_urls.add(new_normalized_url) # Can add here too for earlier filtering
                except Exception as e:
                    print(f"  Error extracting links from {current_url}: {e}")
        
        await page.close()
        await asyncio.sleep(CRAWL_DELAY_SECONDS) # Be polite!

    print(f"\nFinished crawling. Collected content from {len(all_collected_content)} unique pages.")
    return all_collected_content

# --- Main Orchestration ---
async def main():
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    print(f"All scraped data will be saved in: {os.path.abspath(OUTPUT_BASE_DIR)}")
    print(f"\nStarting full website crawl for: \"{START_URL}\"")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Set headless=False to see browser UI
        browser_context = await browser.new_context()

        all_collected_content = await crawl_website(START_URL, browser_context, OUTPUT_BASE_DIR)

        await browser_context.close() # Close browser context
        await browser.close() # Close browser

        print("\n--- All Collected Content for LLM ---")
        if all_collected_content:
            for i, item in enumerate(all_collected_content):
                print(f"\n--- Document {i+1} ---")
                print(f"Source URL: {item.get('url', 'N/A')}")
                print(f"Title: {item.get('title', 'N/A')}")
                print("Content (Excerpt):")
                
                markdown_content = item.get('markdown_content')
                if markdown_content is not None:
                    print(markdown_content[:1000] + ("..." if len(markdown_content) > 1000 else ""))
                else:
                    print("[No content extracted for this page]")
                print("-" * 50)

            combined_llm_input = ""
            for item in all_collected_content:
                markdown_content = item.get('markdown_content')
                if markdown_content is not None and markdown_content.strip():
                    combined_llm_input += f"## Source: {item.get('title', 'N/A')} ({item.get('url', 'N/A')})\n\n"
                    combined_llm_input += f"{markdown_content}\n\n---\n\n"
                else:
                    combined_llm_input += f"## Source: {item.get('title', 'N/A')} ({item.get('url', 'N/A')})\n\n"
                    combined_llm_input += "[Content not available for this page]\n\n---\n\n"


            print("\n--- Combined LLM Input (Full Excerpt) ---")
            print(combined_llm_input[:3000] + ("..." if len(combined_llm_input) > 3000 else ""))
            
            final_combined_filename = os.path.join(OUTPUT_BASE_DIR, "combined_llm_input.md")
            with open(final_combined_filename, "w", encoding="utf-8") as f:
                f.write(combined_llm_input)
            print(f"\nCombined content for LLM saved to '{final_combined_filename}'")

        else:
            print("No content was collected.")

if __name__ == "__main__":
    asyncio.run(main())