import asyncio
from playwright.async_api import async_playwright, Page
import re
from urllib.parse import urljoin, urlparse

# --- Helper for HTML to Markdown (Playwright extracts text, but if you get HTML, use this) ---
def convert_html_to_markdown_for_llm(html_content, base_url=""):
    """
    Converts raw HTML content to Markdown, making it suitable for LLMs.
    Handles relative links if base_url is provided.
    """
    if not html_content:
        return ""

    try:
        from markdownify import markdownify as md
        from bs4 import BeautifulSoup

        # Use BeautifulSoup to parse and resolve relative URLs first
        soup = BeautifulSoup(html_content, 'html.parser')
        for img in soup.find_all('img', src=True):
            img['src'] = urljoin(base_url, img['src'])
        for a in soup.find_all('a', href=True):
            a['href'] = urljoin(base_url, a['href'])

        converter = md.MarkdownConverter(
            strong_em_symbol='**',
            bullets='*',
            code_language='python',
            strip=['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']
        )
        markdown_output = converter.convert(str(soup)) # Convert the modified soup back to string

        # Further cleanup for LLM readability
        markdown_output = re.sub(r'\n\s*\n', '\n\n', markdown_output).strip()
        markdown_output = re.sub(r'\[]\(([^)]+)\)', r'(\1)', markdown_output)
        markdown_output = re.sub(r'\n\n\n+', '\n\n', markdown_output)
        return markdown_output
    except ImportError:
        print("Warning: BeautifulSoup4 or markdownify not installed. Cannot convert HTML to Markdown.")
        return html_content # Return raw HTML if markdownify is not available
    except Exception as e:
        print(f"Error converting HTML to Markdown: {e}")
        return html_content


async def scrape_with_playwright(url: str, query: str = None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Set headless=False to see the browser UI
        page = await browser.new_page()

        print(f"Navigating to {url}")
        await page.goto(url)

        # 1. Take a screenshot
        screenshot_path = "playwright_screenshot.png"
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")

        # 2. Get page title
        title = await page.title()
        print(f"\nPage Title: {title}")

        # 3. Get main heading (H1)
        main_heading_locator = page.locator("h1").first
        main_heading = await main_heading_locator.text_content() if await main_heading_locator.is_visible() else "N/A"
        print(f"Main Heading: {main_heading}")

        # 4. Extract text from all paragraphs within a specific content area
        # Use a more specific selector if available, e.g., 'div.post-content p'
        # For demonstration, let's target all paragraphs within the body
        paragraphs = await page.locator("body p").all_text_contents()
        content_text = "\n\n".join(paragraphs)
        print(f"\n--- Extracted Paragraph Content (excerpt) ---")
        print(content_text[:500] + "..." if len(content_text) > 500 else content_text)

        # 5. Extract all links (href and text)
        all_links = []
        # Use a more specific selector if available, e.g., 'div.main-content a'
        link_elements = await page.locator("a").all() # Get all 'a' elements
        for link_element in link_elements:
            href = await link_element.get_attribute("href")
            text = await link_element.text_content()
            if href:
                all_links.append({"text": text.strip(), "href": urljoin(url, href)})
        print(f"\n--- Extracted Links (first 5) ---")
        for i, link in enumerate(all_links[:5]):
            print(f"  Text: {link['text']}, URL: {link['href']}")
        if len(all_links) > 5:
            print(f"  ...and {len(all_links) - 5} more links.")

        # 6. Interact with a search bar (if a query is provided)
        if query:
            print(f"\n--- Searching for '{query}' ---")
            # This is highly site-specific. You need to inspect the target website.
            # Common selectors: input[name="q"], input[type="search"], #search-input
            search_input_locator = page.locator('input[name="q"], input[type="search"], #search-input').first

            if await search_input_locator.is_visible():
                await search_input_locator.fill(query)
                # Attempt to click a search button or press Enter
                search_button_locator = page.locator('button[type="submit"], input[type="submit"], [aria-label="Search"]').first
                
                if await search_button_locator.is_visible():
                    print("  Clicking search button...")
                    await search_button_locator.click()
                    await page.wait_for_load_state('networkidle') # Wait for new content to load
                    print(f"  Navigated to: {page.url}")
                else:
                    print("  No obvious search button found, pressing Enter...")
                    await search_input_locator.press("Enter")
                    await page.wait_for_load_state('networkidle')
                    print(f"  Navigated to: {page.url}")
            else:
                print("  Search input not found on the page with common selectors.")

        await browser.close()
        print("\nBrowser closed.")

        return {
            "url": url,
            "title": title,
            "main_heading": main_heading,
            "content_text": content_text,
            "links": all_links,
            "screenshot_path": screenshot_path
        }

if __name__ == "__main__":
    # Ensure BeautifulSoup4 and markdownify are installed if you plan to use the HTML to Markdown converter
    # pip install beautifulsoup4 markdownify

    target_url = "https://www.google.com" # Or any other dynamic website
    search_term = "What is deepMind?"

    # Example 1: Scrape a general page
    print("--- Playwright Example: General Page Scraping ---")
    asyncio.run(scrape_with_playwright(target_url))

    # Example 2: Scrape a page and perform a search
    print("\n--- Playwright Example: Performing a Search ---")
    asyncio.run(scrape_with_playwright(target_url, search_term))