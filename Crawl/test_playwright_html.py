import asyncio
from playwright.async_api import async_playwright

async def get_html_with_playwright(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle") # Wait for network to be idle

        # Get the full rendered HTML content of the page
        html_content = await page.content()
        print(f"--- Full HTML Content for {url} (first 500 chars) ---")
        print(html_content[:500] + "..." if len(html_content) > 500 else html_content)

        # Or get the inner HTML of a specific element
        try:
            specific_element_html = await page.locator("#main-content").inner_html()
            print(f"\n--- HTML of #main-content (first 200 chars) ---")
            print(specific_element_html[:200] + "..." if len(specific_element_html) > 200 else specific_element_html)
        except Exception:
            print("\n#main-content element not found or could not get inner HTML.")

        # Or just the text content of a specific element
        try:
            specific_element_text = await page.locator("h2.section-title").text_content()
            print(f"\n--- Text content of h2.section-title ---")
            print(specific_element_text)
        except Exception:
            print("\nh2.section-title element not found or could not get text content.")

        await browser.close()

if __name__ == "__main__":
    test_url = "https://www.example.com" # Replace with a dynamic website if you want to see the difference
    asyncio.run(get_html_with_playwright(test_url))