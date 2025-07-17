from firecrawl import FirecrawlApp, ScrapeOptions, JsonConfig
from pydantic import BaseModel

FC_API_KEY='fc-292788c20ab34ddaa94265f76f1ba335'
app = FirecrawlApp(api_key=FC_API_KEY)

# Scrape a website:
scrape_result = app.scrape_url('https://docs.firecrawl.dev/introduction', formats=['markdown', 'html'])
print(scrape_result)

# Crawling
# Used to crawl a URL and all accessible subpages. 
# This submits a crawl job and returns a job ID to check the status of the crawl.
# Crawl a website:
crawl_result = app.crawl_url(
  'https://firecrawl.dev', 
  limit=10, 
  scrape_options=ScrapeOptions(formats=['markdown', 'html']),
)
print(crawl_result)

# Extraction

# With LLM extraction, you can easily extract structured data from any URL. We support pydantic schemas to make it easier for you too. Here is how you to use it:
class ExtractSchema(BaseModel):
    company_mission: str
    supports_sso: bool
    is_open_source: bool
    is_in_yc: bool

json_config = JsonConfig(
    schema=ExtractSchema
)

llm_extraction_result = app.scrape_url(
    'https://firecrawl.dev',
    formats=["json"],
    json_options=json_config,
    only_main_content=False,
    timeout=120000
)

print(llm_extraction_result.json)

# Interacting with the page with Actions
# Firecrawl allows you to perform various actions on a web page before scraping its content. This is particularly useful for interacting with dynamic content, navigating through pages, or accessing content that requires user interaction.
# Here is an example of how to use actions to navigate to google.com, search for Firecrawl, click on the first result, and take a screenshot.
# It is important to almost always use the wait action before/after executing other actions to give enough time for the page to load.

# Scrape a website:
scrape_result = app.scrape_url('firecrawl.dev', 
    formats=['markdown', 'html'], 
    actions=[
        {"type": "wait", "milliseconds": 2000},
        {"type": "click", "selector": "textarea[title=\"Search\"]"},
        {"type": "wait", "milliseconds": 2000},
        {"type": "write", "text": "firecrawl"},
        {"type": "wait", "milliseconds": 2000},
        {"type": "press", "key": "ENTER"},
        {"type": "wait", "milliseconds": 3000},
        {"type": "click", "selector": "h3"},
        {"type": "wait", "milliseconds": 3000},
        {"type": "scrape"},
        {"type": "screenshot"}
    ]
)
print(scrape_result)