RAG System:
Knowledge Base (Vector Database): Stores embedded chunks of crawled business, marketing, and management content.
Retriever: Queries the knowledge base to find relevant information based on the user's startup idea.
Augmenter: Combines the retrieved information with the user's idea and a specific prompt for the LLM.
LLM Agent: Receives the augmented prompt and generates the harsh critique.
Web Crawler (Python/Playwright): Collects the raw HTML content for the RAG knowledge base.

1. Knowledge Required for the RAG System
2. How to Crawl the Web to Get Such Knowledge

