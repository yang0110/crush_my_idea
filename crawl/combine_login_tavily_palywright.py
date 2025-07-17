import os
import re
import asyncio
import hashlib
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Page, BrowserContext

# Ensure these are installed:
# pip install tavily-python markdownify beautifulsoup4 playwright
# playwright install

from tavily import TavilyClient
from markdownify import markdownify as md
from bs4 import BeautifulSoup

# --- Configuration ---
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable not set.")

# --- LinkedIn Specific Configuration (Highly Sensitive!) ---
LINKEDIN_USERNAME = os.environ.get("LINKEDIN_USERNAME") # Store securely!
LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD") # Store securely!
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_HOME_URL = "https://www.linkedin.com/feed/" # Or any known post-login URL
USER_DATA_DIR = "playwright_user_data" # Directory to store Playwright session data (cookies, etc.)

SEARCH_QUERY = "DeepMind latest research on AI ethics"
MAX_SEARCH_RESULTS_TO_PROCESS = 3
MAX_PAGES_TO_EXTRACT_PER_DOMAIN = 1

OUTPUT_BASE_DIR = "scraped_data"

# Initialize Tavily Client
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# --- Helper Functions (Same as before) ---

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
    """Generates a safe filename from a URL."""
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    parsed = urlparse(url)
    path_segment = parsed.path.strip('/').replace('/', '_').replace('.', '_').replace('-', '_')
    if path_segment:
        clean_name = f"{path_segment[:50]}_{url_hash[:8]}"
    else:
        clean_name = url_hash
    return f"{clean_name}{suffix}"

async def step1_search_and_get_urls(query: str, max_results: int) -> list[dict]:
    """
    Performs a Tavily search and returns a list of relevant URL information.
    """
    print(f"Step 1: Performing Tavily search for: \"{query}\"")
    response = tavily_client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_raw_content=False,
        include_images=False
    )

    search_results_info = []
    if response and response['results']:
        for result in response['results']:
            search_results_info.append({
                "title": result.get("title", "No Title"),
                "url": result.get("url", "No URL"),
                "score": result.get("score", 0.0),
                "raw_content": None
            })
        print(f"  Found {len(search_results_info)} search results.")
    else:
        print("  No search results found.")
    return search_results_info

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

# --- NEW: Login Handling Function ---
async def login_to_linkedin(context: BrowserContext, username: str, password: str, login_url: str, home_url: str) -> bool:
    """
    Handles logging into LinkedIn using a Playwright persistent context.
    If already logged in, it will skip.
    """
    print(f"\nAttempting to log in to LinkedIn at {login_url}...")
    page = await context.new_page()
    try:
        await page.goto(home_url, wait_until="load", timeout=30000)
        # Check if already logged in (e.g., by checking for a known element on the home page)
        # LinkedIn's homepage after login might have a specific global navigation or feed element
        try:
            await page.wait_for_selector('div.global-nav__primary-items', timeout=10000)
            print("  Already logged in to LinkedIn, skipping login steps.")
            return True # Already logged in
        except:
            print("  Not logged in, proceeding with login process.")

        await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)

        # Fill in credentials (use more robust locators if possible, e.g., byLabel, byPlaceholder)
        # LinkedIn often uses IDs: "session_key" for username, "session_password" for password
        await page.fill('#session_key', username)
        await page.fill('#session_password', password)

        # Click the sign-in button
        # The button might have data attributes, text, or a specific type/class
        # Look for the button using Playwright's Inspector (npx playwright codegen linkedin.com)
        await page.click('button[type="submit"][data-litms-control-urn="login-submit"]')
        # Or a more general one: await page.click('button[type="submit"]')

        # Wait for navigation to the home page or a known post-login element
        await page.wait_for_url(home_url, timeout=60000) # Wait up to 60 seconds for redirect
        await page.wait_for_selector('div.global-nav__primary-items', timeout=10000) # Verify an element
        print("  Successfully logged in to LinkedIn!")
        return True
    except Exception as e:
        print(f"  Failed to log in to LinkedIn: {e}")
        # Capture a screenshot on failure for debugging
        await page.screenshot(path=os.path.join(OUTPUT_BASE_DIR, "linkedin_login_failure.png"))
        print(f"  Screenshot of login failure saved to {os.path.join(OUTPUT_BASE_DIR, 'linkedin_login_failure.png')}")
        return False
    finally:
        await page.close()


async def step2_extract_content_from_urls_with_playwright(
    urls_info: list[dict], browser_context: BrowserContext, base_output_dir: str
) -> list[dict]:
    """
    Uses Playwright to visit each URL, extract its full HTML content,
    converts it to Markdown, and saves both to files.
    """
    print("\nStep 2: Extracting content from URLs using Playwright...")
    extracted_content_list = []
    
    for item in urls_info:
        url = item['url']
        print(f"  Visiting: {url}")
        
        # Check if it's a LinkedIn URL and we need to ensure login
        is_linkedin_url = "linkedin.com" in urlparse(url).netloc
        if is_linkedin_url:
            # For LinkedIn, ensure login and then navigate
            if not (LINKEDIN_USERNAME and LINKEDIN_PASSWORD):
                print(f"  Skipping LinkedIn URL {url} because LinkedIn credentials are not provided.")
                extracted_content_list.append({
                    "title": item['title'],
                    "url": url,
                    "markdown_content": "[LinkedIn content skipped: credentials missing]",
                    "html_content": "[LinkedIn content skipped: credentials missing]"
                })
                continue
            
            # The context should already be logged in from main if successful.
            # Just create a new page in the logged-in context and proceed.
            page = await browser_context.new_page()
            # It's good practice to navigate to the LinkedIn home first to confirm session
            # await page.goto(LINKEDIN_HOME_URL, wait_until="load", timeout=30000)
            # await page.wait_for_selector('div.global-nav__primary-items', timeout=10000) # Optional check
            # print(f"  Confirmed active LinkedIn session before navigating to {url}")
        else:
            page = await browser_context.new_page()

        markdown_content, html_content = await extract_content_and_save_with_playwright(page, url, base_output_dir)
        await page.close()

        if markdown_content:
            extracted_content_list.append({
                "title": item['title'],
                "url": url,
                "markdown_content": markdown_content,
                "html_content": html_content
            })
        else:
            print(f"  Skipping {url} due to content extraction/saving failure.")
            extracted_content_list.append({
                "title": item['title'],
                "url": url,
                "markdown_content": "[Content not available]",
                "html_content": "[Content not available]"
            })
            
    print(f"  Finished Playwright extraction for {len(extracted_content_list)} URLs.")
    return extracted_content_list

async def step3_crawl_domain_for_more_pages_with_playwright(
    domain_url: str, max_pages: int, browser_context: BrowserContext, base_output_dir: str
) -> list[dict]:
    """
    Crawls a specific domain for more relevant pages using Playwright,
    extracting and saving their HTML and Markdown content. Limited to max_pages.
    """
    print(f"\nStep 3: Recursively crawling domain: {domain_url} for more pages (Max {max_pages})...")
    crawled_pages_info = []
    
    visited_urls = set()
    to_visit_queue = asyncio.Queue()
    await to_visit_queue.put(domain_url)
    visited_urls.add(domain_url)

    parsed_domain = urlparse(domain_url).netloc
    
    # If the domain is LinkedIn, ensure we have credentials.
    is_linkedin_domain = "linkedin.com" in parsed_domain
    if is_linkedin_domain and not (LINKEDIN_USERNAME and LINKEDIN_PASSWORD):
        print(f"  Skipping recursive crawl for LinkedIn domain {domain_url}: credentials not provided.")
        return [] # Don't attempt to crawl if no credentials

    while not to_visit_queue.empty() and len(crawled_pages_info) < max_pages:
        current_url = await to_visit_queue.get()
        print(f"  Crawling (Playwright): {current_url} (Count: {len(crawled_pages_info)}/{max_pages})")

        page = await browser_context.new_page()
        markdown_content, html_content = await extract_content_and_save_with_playwright(page, current_url, base_output_dir)
        
        if markdown_content:
            crawled_pages_info.append({
                "title": f"Crawled Page from {urlparse(current_url).netloc}",
                "url": current_url,
                "markdown_content": markdown_content,
                "html_content": html_content
            })
            
            # Find new links on the current page
            link_elements = await page.locator("a").all()
            for link_element in link_elements:
                href = await link_element.get_attribute("href")
                if href:
                    absolute_url = urljoin(current_url, href)
                    parsed_absolute_url = urlparse(absolute_url)

                    if parsed_absolute_url.scheme in ('http', 'https') and \
                       parsed_absolute_url.netloc == parsed_domain and \
                       absolute_url not in visited_urls:
                        
                        if len(parsed_absolute_url.path.split('/')) < 6 and \
                           not (parsed_absolute_url.path.lower().endswith(('.pdf', '.zip', '.doc', '.docx', '.xls', '.xlsx'))):
                            await to_visit_queue.put(absolute_url)
                            visited_urls.add(absolute_url)
                        
        await page.close()

    print(f"  Finished crawling {domain_url}. Collected {len(crawled_pages_info)} additional pages.")
    return crawled_pages_info

# --- Main Orchestration ---
async def main():
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    print(f"All scraped data will be saved in: {os.path.abspath(OUTPUT_BASE_DIR)}")
    print(f"\nStarting web research for query: \"{SEARCH_QUERY}\"")

    # Define the user data directory for persistent context
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    print(f"Playwright user data (cookies, cache) will be stored in: {os.path.abspath(USER_DATA_DIR)}")

    async with async_playwright() as p:
        # Launch a persistent context
        # This will either load an existing session or create a new one
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True # Set to False for the first run to manually log in
        )
        
        # --- LinkedIn Login Section ---
        # Check if LinkedIn credentials are provided and attempt to log in
        if LINKEDIN_USERNAME and LINKEDIN_PASSWORD:
            print("\nChecking LinkedIn login status...")
            await login_to_linkedin(browser_context, LINKEDIN_USERNAME, LINKEDIN_PASSWORD, LINKEDIN_LOGIN_URL, LINKEDIN_HOME_URL)
        else:
            print("\nLinkedIn credentials (LINKEDIN_USERNAME, LINKEDIN_PASSWORD) not provided. Will not attempt LinkedIn login.")
            print("Note: If search results include LinkedIn URLs, they might be inaccessible.")


        # Step 1: Perform initial search and get relevant URLs
        search_results_info = await step1_search_and_get_urls(SEARCH_QUERY, MAX_SEARCH_RESULTS_TO_PROCESS)

        if not search_results_info:
            print("No initial search results to process. Exiting.")
            await browser_context.close()
            return

        print(f"\nSuccessfully found {len(search_results_info)} initial search results.")

        # Step 2: Extract content from the initial search results using Playwright
        extracted_content_from_search = await step2_extract_content_from_urls_with_playwright(
            search_results_info, browser_context, OUTPUT_BASE_DIR
        )
        all_collected_content = list(extracted_content_from_search)

        # Optional: Further crawl highly relevant domains from the top results
        unique_domains_to_crawl = set()
        for result in search_results_info:
            parsed_url = urlparse(result["url"])
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            if domain and parsed_url.netloc:
                unique_domains_to_crawl.add(domain)
                if len(unique_domains_to_crawl) >= 1:
                    break # Limit to 1 domain for demo recursion
        
        if unique_domains_to_crawl:
            print(f"\nIdentified unique domains for optional deeper crawl: {list(unique_domains_to_crawl)}")
            for domain_url in list(unique_domains_to_crawl):
                crawled_pages = await step3_crawl_domain_for_more_pages_with_playwright(
                    domain_url, MAX_PAGES_TO_EXTRACT_PER_DOMAIN, browser_context, OUTPUT_BASE_DIR
                )
                if crawled_pages:
                    print(f"  Successfully crawled {len(crawled_pages)} additional pages from {domain_url}")
                    for page_info in crawled_pages:
                        if not any(item['url'] == page_info['url'] for item in all_collected_content):
                            all_collected_content.append(page_info)
                else:
                    print(f"  No additional pages crawled from {domain_url}")

        await browser_context.close() # Close persistent context at the end

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