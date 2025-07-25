import asyncio
import re
from datetime import datetime
import os
from bs4 import BeautifulSoup

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def crawl_ycombinator_blogs(num_blogs_to_crawl: int = 100):
    """
    Crawls the Y Combinator blog to extract the most recent N blog posts,
    converts their content to Markdown, and saves them to files.

    Args:
        num_blogs_to_crawl (int): The number of most recent blog posts to crawl and save.
    """
    base_blog_listing_url = "https://www.ycombinator.com/blog"
    output_directory = "ycombinator_blog_markdowns"
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)

    # Dictionary to store unique blog post URLs and their publication dates
    # This helps in de-duplication and sorting by recency
    blog_post_candidates = {} # Format: {full_url: datetime_object}

    print(f"✨ Starting to collect blog post links from {base_blog_listing_url}...")

    # Configure the crawler for the main blog listing page
    # We need to use JavaScript to click the "Load More" button
    listing_page_crawler_config = CrawlerRunConfig(
        cache_mode="bypass", # Always get fresh content for the blog list
        # JavaScript to click the "Load More" button if it exists
        js_code="""
            const loadMoreButton = document.querySelector('button.w-full.text-center.py-6.border-b.border-gray-100.font-bold.text-vc-purple-500');
            if (loadMoreButton) {
                loadMoreButton.click();
                return true; // Indicate that a click occurred
            }
            return false; // Indicate no click occurred
        """,
        # After clicking, wait for a new blog post element to appear
        wait_for=".ycdc-blog-post:last-child",
        page_timeout=30000 # Increase timeout for dynamic loading
    )

    # Use a maximum number of "Load More" clicks as a safeguard
    max_load_more_clicks = 30 # Adjust based on how many clicks are needed for ~100 blogs

    # Initialize AsyncWebCrawler. headless=True means the browser will not be visible.
    # Set to False for debugging to see the browser actions.
    browser_config = BrowserConfig(headless=True) 

    async with AsyncWebCrawler(config=browser_config) as crawler:
        current_url_for_listing = base_blog_listing_url

        for i in range(max_load_more_clicks):
            print(f"  Fetching blog listing page/section {i+1}...")
            
            # Perform the crawl. If js_code returns true, it means the button was clicked.
            # The wait_for will then ensure new content has a chance to load.
            try:
                result = await crawler.arun(url=current_url_for_listing, config=listing_page_crawler_config)
            except Exception as e:
                print(f"  Error fetching listing page {current_url_for_listing}: {e}")
                break

            if not result.html:
                print("  No HTML received for listing page. Stopping collection.")
                break

            soup = BeautifulSoup(result.html, 'html.parser')
            
            # Find all blog post card elements on the current page view
            post_elements = soup.select('li.ycdc-blog-post')

            if not post_elements and i > 0: # If no posts found after initial load, and it's not the first iteration
                print("  No new blog posts found after 'Load More' click. Stopping pagination.")
                break

            new_posts_added_in_iteration = False
            for post_element in post_elements:
                link_tag = post_element.select_one('.ycdc-blog-post-card-title a')
                date_tag = post_element.select_one('.ycdc-blog-post-card-date')

                if link_tag and date_tag:
                    relative_href = link_tag.get('href')
                    date_text = date_tag.text.strip() # e.g., "Jul 23, 2024"

                    if relative_href and relative_href.startswith('/blog/'):
                        full_blog_url = f"https://www.ycombinator.com{relative_href}"
                        try:
                            # Convert date string to datetime object for proper sorting
                            post_date = datetime.strptime(date_text, '%b %d, %Y')
                            if full_blog_url not in blog_post_candidates:
                                blog_post_candidates[full_blog_url] = post_date
                                new_posts_added_in_iteration = True
                        except ValueError:
                            print(f"  Warning: Could not parse date '{date_text}' for {full_blog_url}. Skipping date sorting for this entry.")
                            blog_post_candidates[full_blog_url] = datetime.min # Assign min date to push it to the end if unable to parse

            print(f"  Collected {len(blog_post_candidates)} unique blog post links so far.")

            # Check if the "Load More" button is still present on the page
            load_more_button_on_page = soup.select_one('button.w-full.text-center.py-6.border-b.border-gray-100.font-bold.text-vc-purple-500')
            
            # Stop if we have enough candidates, no new posts found in this iteration, or no more "Load More" button
            if len(blog_post_candidates) >= num_blogs_to_crawl * 1.5 or not new_posts_added_in_iteration or not load_more_button_on_page:
                print("  Stopping pagination: Collected sufficient links, or no more 'Load More' button/new posts.")
                break
            
            # For the next iteration, we'll continue with the current_url_for_listing,
            # letting js_code handle the navigation (button click) on the existing page content.


    if not blog_post_candidates:
        print("🔴 No blog posts found after collection. Exiting.")
        return

    # Sort the collected blog posts by date, most recent first
    # Using lambda function to sort by the datetime object stored in the dictionary values
    sorted_blog_urls = sorted(blog_post_candidates.keys(), 
                              key=lambda url: blog_post_candidates[url], 
                              reverse=True)
    
    # Take only the desired number of most recent blogs
    top_blogs_to_process = sorted_blog_urls[:num_blogs_to_crawl]

    print(f"\n✅ Successfully collected {len(blog_post_candidates)} blog post links. ")
    print(f"📚 Proceeding to crawl the top {len(top_blogs_to_process)} most recent blog posts...")

    # Configure the crawler for individual blog post pages (no special JS needed)
    individual_blog_crawler_config = CrawlerRunConfig(cache_mode="bypass")

    for i, blog_url in enumerate(top_blogs_to_process):
        print(f"  ({i+1}/{len(top_blogs_to_process)}) Crawling: {blog_url}")
        try:
            # Crawl the individual blog post page
            blog_result = await crawler.arun(url=blog_url, config=individual_blog_crawler_config)

            if not blog_result.markdown:
                print(f"    ⚠️ Warning: No markdown content extracted for {blog_url}. Skipping.")
                continue

            # Use BeautifulSoup to extract the precise title and datetime from the HTML
            # This is more reliable than trying to parse from markdown or assuming structure
            blog_soup = BeautifulSoup(blog_result.html, 'html.parser')
            
            # Find the title using its specific classes
            title_tag = blog_soup.select_one('h1.font-bold.text-\\[32px\\].text-vc-purple-900.leading-snug-38')
            # Find the time tag and get its 'datetime' attribute (which is in ISO format)
            datetime_tag = blog_soup.select_one('time[datetime]')

            blog_title = title_tag.text.strip() if title_tag else "Untitled_Blog_Post"
            # Get ISO format date (e.g., "2024-07-23")
            post_datetime_iso = datetime_tag['datetime'] if datetime_tag and 'datetime' in datetime_tag.attrs else "undated"

            # Sanitize the title for use in a filename
            # Replace non-alphanumeric, non-space, non-underscore, non-hyphen characters
            sanitized_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', blog_title).replace(' ', '_')
            
            # Format datetime for filename (e.g., "YYYY-MM-DD")
            try:
                file_datetime_part = datetime.strptime(post_datetime_iso, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                file_datetime_part = "undated"
                print(f"    ⚠️ Warning: Could not parse ISO date '{post_datetime_iso}' for filename for {blog_title}. Using 'undated'.")

            # Construct the filename: "Blog_Title_YYYY-MM-DD.md"
            filename = f"{sanitized_title}_{file_datetime_part}.md"
            filepath = os.path.join(output_directory, filename)

            # Save the Markdown content to the file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {blog_title}\n\n") # Add title as a Markdown heading
                f.write(f"**Published Date:** {post_datetime_iso}\n\n") # Add date
                f.write(blog_result.markdown) # The main Markdown content
            print(f"    ✅ Saved: {filepath}")

        except Exception as e:
            print(f"    ❌ Error processing {blog_url}: {e}")

    print("\n🎉 Deep crawling completed. Check the 'ycombinator_blog_markdowns' directory for your files.")

if __name__ == "__main__":
    # Run the asynchronous function
    asyncio.run(crawl_ycombinator_blogs(num_blogs_to_crawl=100))
