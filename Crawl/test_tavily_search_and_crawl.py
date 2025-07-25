import os
from tavily import TavilyClient
from markdownify import markdownify as md
import re
import asyncio # For asynchronous operations with extract, which is more efficient
from urllib.parse import urljoin, urlparse

# --- Configuration ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") # Recommended: set this as an environment variable
if not TAVILY_API_KEY:
    print("Error: TAVILY_API_KEY environment variable not set.")
    print("Please set the TAVILY_API_KEY environment variable (e.g., in your shell or .env file).")
    exit()

SEARCH_QUERY = "what is deepmind?"
MAX_SEARCH_RESULTS_TO_PROCESS = 5 # Number of top search results to investigate
MAX_PAGES_TO_EXTRACT_PER_DOMAIN = 3 # Max additional internal pages to extract from a domain

# Initialize Tavily Client
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# --- Helper for HTML to Markdown Conversion (if Tavily returns HTML) ---
def convert_html_to_markdown_for_llm(html_content, base_url=""):
    """
    Converts raw HTML content to Markdown, making it suitable for LLMs.
    Handles relative links if base_url is provided.
    """
    if not html_content:
        return ""

    class CustomMarkdownConverter(md.MarkdownConverter):
        def convert_img(self, el, text, parent_tags):
            src = el.get('src')
            alt = el.get('alt', '')
            if src:
                absolute_src = urljoin(base_url, src)
                return f"![{alt}]({absolute_src})\n\n"
            return ""

        def convert_a(self, el, text, parent_tags):
            href = el.get('href')
            if href:
                absolute_href = urljoin(base_url, href)
                return f"[{text}]({absolute_href})"
            return text

    converter = CustomMarkdownConverter(
        strong_em_symbol='**',
        bullets='*',
        code_language='python', # Default code language hint
        # Keep important tags, strip others that might clutter LLM input
        strip=['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']
    )

    markdown_output = converter.convert(html_content)

    # Further cleanup for LLM readability
    markdown_output = re.sub(r'\n\s*\n', '\n\n', markdown_output).strip() # Reduce multiple blank lines
    markdown_output = re.sub(r'\[]\(([^)]+)\)', r'(\1)', markdown_output) # Convert empty link text to just the URL in parentheses
    # Remove excessive blank lines at the start/end or within
    markdown_output = re.sub(r'\n\n\n+', '\n\n', markdown_output)
    
    return markdown_output

# --- 1. Perform Search (using Tavily Search API) ---
async def step1_search_and_get_urls(query, max_results):
    """
    Performs a Tavily search and returns a list of result URLs and titles.
    """
    print(f"Step 1: Performing Tavily Search for: '{query}'")
    try:
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            include_raw_content=False, # Don't get raw content yet, we'll use extract for more control
            search_depth="advanced" # "advanced" search for better initial results
        )
        
        urls_to_process = []
        if response and "results" in response:
            for result in response["results"]:
                urls_to_process.append({
                    "title": result.get("title"),
                    "url": result.get("url")
                })
        return urls_to_process
    except Exception as e:
        print(f"Error during Tavily Search: {e}")
        return []

# --- 2. Extract Content from Specific URLs (using Tavily Extract API) ---
async def step2_extract_content_from_urls(urls_info):
    """
    Extracts cleaned content from a list of URLs using Tavily Extract API.
    Processes URLs in batches for efficiency.
    """
    extracted_data = []
    
    # Tavily Extract API allows up to 20 URLs per call.
    # We'll batch them to respect this limit and maximize efficiency.
    batch_size = 20 
    
    for i in range(0, len(urls_info), batch_size):
        batch_urls_info = urls_info[i:i + batch_size]
        urls_to_extract = [item["url"] for item in batch_urls_info]
        
        print(f"Step 2: Extracting content from batch of {len(urls_to_extract)} URLs.")
        try:
            # Using client.extract for specific URL content extraction
            extract_response = tavily_client.extract(
                urls=urls_to_extract,
                extract_depth="advanced", # "advanced" for more comprehensive content retrieval
                format="markdown" # Request content directly in markdown format
            )

            if extract_response and "results" in extract_response:
                for extracted_result in extract_response["results"]:
                    original_url = extracted_result.get("url")
                    # Find original title from urls_info
                    original_title = next((item["title"] for item in urls_info if item["url"] == original_url), original_url)

                    extracted_data.append({
                        "title": original_title,
                        "url": original_url,
                        "markdown_content": extracted_result.get("raw_content") # Tavily returns 'raw_content' here
                    })
            if extract_response and "failed_results" in extract_response:
                for failed_url_info in extract_response["failed_results"]:
                    print(f"  Failed to extract: {failed_url_info.get('url')} - Error: {failed_url_info.get('error')}")

        except Exception as e:
            print(f"Error during Tavily Extract for batch: {e}")
            
    return extracted_data

# --- Optional: Step 3 - Crawl for more depth (if needed) ---
# This is more for building a comprehensive knowledge base of a *single* domain.
# For "multiple pages in top listed search result", Step 1 + Step 2 is usually sufficient.
async def step3_crawl_domain_for_more_pages(base_url, max_pages_to_extract):
    """
    Crawls a single domain to extract more internal pages.
    This is best used after `search` and `extract` for a highly relevant domain.
    Note: Tavily Crawl is in BETA and its pricing model is different (per 5 successful URL extractions).
    """
    print(f"Step 3 (Optional): Initiating crawl for domain: {base_url}")
    domain_content = []
    try:
        crawl_response = tavily_client.crawl(
            url=base_url,
            max_depth=1, # Crawl only the immediate links from the base URL
            limit=max_pages_to_extract, # Max number of links to process
            include_images=False,
            format="markdown", # Request markdown content directly
            # selectPaths=["/docs/.*"], # Example: Only crawl pages under /docs/
            # excludePaths=["/admin/.*"] # Example: Exclude admin pages
        )

        if crawl_response and "results" in crawl_response:
            for result in crawl_response["results"]:
                domain_content.append({
                    "url": result.get("url"),
                    "markdown_content": result.get("rawContent") # Note 'rawContent' for crawl
                })
        
        if crawl_response and "failed_results" in crawl_response:
            for failed_url_info in crawl_response["failed_results"]:
                print(f"  Failed to crawl: {failed_url_info.get('url')} - Error: {failed_url_info.get('error')}")

        return domain_content
    except Exception as e:
        print(f"Error during Tavily Crawl for {base_url}: {e}")
        return []

# --- Main Orchestration ---
async def main():
    print(f"Starting web research for query: \"{SEARCH_QUERY}\"\n")

    # Step 1: Perform initial search and get relevant URLs
    search_results_info = await step1_search_and_get_urls(SEARCH_QUERY, MAX_SEARCH_RESULTS_TO_PROCESS)

    if not search_results_info:
        print("No initial search results to process. Exiting.")
        return

    print(f"\nSuccessfully found {len(search_results_info)} initial search results.")

    # Step 2: Extract content from the initial search results
    extracted_content_from_search = await step2_extract_content_from_urls(search_results_info)

    all_collected_content = []
    for item in extracted_content_from_search:
        # If Tavily returns HTML and you want custom markdownify logic:
        # item['markdown_content'] = convert_html_to_markdown_for_llm(item['markdown_content'], item['url'])
        all_collected_content.append(item)


    # Optional: Further crawl highly relevant domains from the top results
    # This part is more complex and depends on *which* specific domains
    # you want to "spider" more deeply after identifying them in search.
    # For demonstration, let's pick the first 2 unique domains from the search results.
    unique_domains_to_crawl = set()
    for result in search_results_info:
        parsed_url = urlparse(result["url"])
        domain = parsed_url.netloc
        if domain: # Ensure domain is not empty
            unique_domains_to_crawl.add(f"{parsed_url.scheme}://{domain}")
            if len(unique_domains_to_crawl) >= 2: # Limit for demo
                break
    
    if unique_domains_to_crawl:
        print(f"\nIdentified unique domains for optional deeper crawl: {list(unique_domains_to_crawl)}")
        for domain_url in list(unique_domains_to_crawl):
            # Crawl for more pages within this specific domain
            crawled_pages = await step3_crawl_domain_for_more_pages(domain_url, MAX_PAGES_TO_EXTRACT_PER_DOMAIN)
            if crawled_pages:
                print(f"  Successfully crawled {len(crawled_pages)} additional pages from {domain_url}")
                for page in crawled_pages:
                    # Filter out pages already extracted from initial search, if needed
                    # (simple check, could be more robust)
                    if not any(item['url'] == page['url'] for item in all_collected_content):
                        all_collected_content.append({
                            "title": f"Crawled Page from {domain_url}", # Generic title for crawled pages
                            "url": page['url'],
                            "markdown_content": page['markdown_content']
                        })
            else:
                print(f"  No additional pages crawled from {domain_url}")


    # --- Final Output for LLM ---
    print("\n--- All Collected Content for LLM ---")
    if all_collected_content:
        for i, item in enumerate(all_collected_content):
            print(f"\n--- Document {i+1} ---")
            print(f"Source URL: {item.get('url', 'N/A')}")
            print(f"Title: {item.get('title', 'N/A')}")
            print("Content (Excerpt):")
            # Limit printing to avoid flooding console
            print(item['markdown_content'][:1000] + ("..." if len(item['markdown_content']) > 1000 else ""))
            print("-" * 50)

        # Combine all content into a single string for the LLM
        combined_llm_input = ""
        for item in all_collected_content:
            combined_llm_input += f"## Source: {item.get('title', 'N/A')} ({item.get('url', 'N/A')})\n\n"
            combined_llm_input += f"{item['markdown_content']}\n\n---\n\n"

        print("\n--- Combined LLM Input (Full Excerpt) ---")
        print(combined_llm_input[:3000] + ("..." if len(combined_llm_input) > 3000 else ""))
        
        # Save to a file for later use
        with open("deepmind_research_content.md", "w", encoding="utf-8") as f:
            f.write(combined_llm_input)
        print("\nCombined content saved to 'deepmind_research_content.md'")

    else:
        print("No content was collected.")

# Run the asynchronous main function
if __name__ == "__main__":
    asyncio.run(main())