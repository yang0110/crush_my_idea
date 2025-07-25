import os
from tavily import TavilyClient
from markdownify import markdownify as md
import re

# --- Configuration ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") # Recommended: set this as an environment variable
if not TAVILY_API_KEY:
    # If not set as env var, prompt or hardcode for testing (not recommended for production)
    # TAVILY_API_KEY = "YOUR_TAVILY_API_KEY_HERE" # Replace with your actual key for testing
    print("Error: TAVILY_API_KEY environment variable not set.")
    print("Please set the TAVILY_API_KEY environment variable or replace the placeholder.")
    exit()

SEARCH_QUERY = "what is deepmind?"
MAX_SEARCH_RESULTS = 5 # Number of search results to retrieve from Tavily

# --- 1. & 2. Use Python code to call Tavily Search Engine ---
def perform_tavily_search(query, max_results=5, include_raw_content=False, search_depth="basic"):
    """
    Performs a search using Tavily API and returns the response.
    :param query: The search query string.
    :param max_results: Maximum number of search results to return (up to 20).
    :param include_raw_content: If True, Tavily will include the cleaned HTML/text content of each result.
                                You can set this to "markdown" to get content directly in markdown.
    :param search_depth: "basic" for faster results (1 credit), "advanced" for more comprehensive search (2 credits).
    :return: Tavily API response dictionary.
    """
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

    print(f"Searching Tavily for: '{query}' with max_results={max_results}, include_raw_content={include_raw_content}, depth={search_depth}")

    try:
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            include_raw_content=include_raw_content, # Get the content of the pages
            search_depth=search_depth # "basic" or "advanced"
        )
        return response
    except Exception as e:
        print(f"Error calling Tavily API: {e}")
        return None

# --- 3. The search engine returns the search resulting links ---
# Tavily's response directly contains the links and optionally content.
def extract_links_and_content(tavily_response):
    """
    Extracts search result links, titles, and content (if available) from Tavily's response.
    """
    extracted_data = []
    if tavily_response and "results" in tavily_response:
        for result in tavily_response["results"]:
            item = {
                "title": result.get("title"),
                "url": result.get("url"),
                "content": result.get("content") # This will be the raw content if requested
            }
            extracted_data.append(item)
    return extracted_data

# --- 4. A Python code that reads the raw HTML and returns as markdown ---
# Tavily can often return markdown directly if you set include_raw_content="markdown".
# However, if it returns HTML and you need further specific formatting/cleaning,
# you can use markdownify.
def convert_html_to_markdown(html_content, url=""):
    """
    Converts raw HTML content to Markdown.
    Includes handling for relative links and basic cleanup.
    """
    if not html_content:
        return ""

    class CustomMarkdownConverter(md.MarkdownConverter):
        def convert_img(self, el, text, parent_tags):
            src = el.get('src')
            alt = el.get('alt', '')
            if src:
                absolute_src = re.sub(r'https?://(?:www\.)?|\/$', '', src) if src.startswith("http") else src
                # If you need absolute URLs, use urljoin, but for LLM, relative often works or just the path
                # absolute_src = urljoin(url, src) # Use this if you need full absolute URLs
                return f"![{alt}]({absolute_src})\n\n"
            return ""

        def convert_a(self, el, text, parent_tags):
            href = el.get('href')
            if href:
                absolute_href = re.sub(r'https?://(?:www\.)?|\/$', '', href) if href.startswith("http") else href
                # absolute_href = urljoin(url, href) # Use this if you need full absolute URLs
                return f"[{text}]({absolute_href})"
            return text

    converter = CustomMarkdownConverter(
        strong_em_symbol='**',
        bullets='*',
        code_language='python'
    )

    markdown_output = converter.convert(html_content)

    # Further cleanup
    markdown_output = re.sub(r'\n\s*\n', '\n\n', markdown_output).strip() # Reduce multiple blank lines
    markdown_output = re.sub(r'\[]\(([^)]+)\)', r'(\1)', markdown_output) # Convert empty link text to just the URL in parentheses
    markdown_output = re.sub(r'^\s*$', '', markdown_output, flags=re.MULTILINE) # Remove empty lines that might remain
    
    return markdown_output

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Search query: \"{SEARCH_QUERY}\"")

    # Step 1 & 2: Perform search with Tavily, asking for raw content
    # We ask for "markdown" content directly from Tavily if possible,
    # otherwise we get "true" (HTML) and convert it.
    tavily_response = perform_tavily_search(
        SEARCH_QUERY,
        max_results=MAX_SEARCH_RESULTS,
        include_raw_content=True, # You can try "markdown" here if your Tavily plan supports it
        search_depth="advanced" # Use "advanced" for better content extraction, costs 2 credits/req
    )

    if tavily_response:
        # Step 3: Extract links and content from the Tavily response
        results_data = extract_links_and_content(tavily_response)

        if not results_data:
            print("No search results found from Tavily.")
        else:
            print(f"\nFound {len(results_data)} search results from Tavily.")
            all_content_for_llm = []

            for i, result in enumerate(results_data):
                print(f"\n--- Result {i+1} ---")
                print(f"Title: {result.get('title', 'N/A')}")
                print(f"URL: {result.get('url', 'N/A')}")

                raw_page_content = result.get('content')
                if raw_page_content:
                    # Tavily typically returns already cleaned text or markdown when include_raw_content is True/markdown
                    # If it's still HTML, use markdownify. Otherwise, it's ready.
                    if raw_page_content.strip().startswith("<"): # Simple check if it looks like HTML
                        markdown_page_content = convert_html_to_markdown(raw_page_content, result.get('url'))
                        print("\n  --- Page Content (Markdown - converted from HTML) ---")
                    else:
                        markdown_page_content = raw_page_content
                        print("\n  --- Page Content (Markdown/Text from Tavily) ---")

                    print(markdown_page_content[:1000] + ("..." if len(markdown_page_content) > 1000 else "")) # Print excerpt
                    all_content_for_llm.append({
                        "source_url": result.get('url'),
                        "title": result.get('title'),
                        "markdown_content": markdown_page_content
                    })
                else:
                    print("  No raw content retrieved for this link (Tavily might not have extracted it, or it was not requested).")

            # This `all_content_for_llm` list now contains structured data
            # ready to be fed into your LLM.
            print("\n--- All Collected Content for LLM ---")
            for item in all_content_for_llm:
                print(f"URL: {item['source_url']}")
                print(f"Title: {item['title']}")
                # print(f"Content Length: {len(item['markdown_content'])}") # Uncomment to see length
                print("-" * 30)

            # Example: Combine content into a single string for LLM input
            combined_llm_input = ""
            for item in all_content_for_llm:
                combined_llm_input += f"## Source: {item['title']} ({item['source_url']})\n\n"
                combined_llm_input += f"{item['markdown_content']}\n\n---\n\n"

            print("\n--- Combined LLM Input Excerpt ---")
            print(combined_llm_input[:2000] + ("..." if len(combined_llm_input) > 2000 else ""))

    else:
        print("Failed to get a response from Tavily. Check your API key and network connection.")