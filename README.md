This is a fantastic idea for an app! "Your Idea Is Bullshit" is a catchy name that perfectly sets the expectation for a brutally honest critique. Building this requires a robust RAG (Retrieval Augmented Generation) system to ensure the LLM's criticism is grounded in real-world business, marketing, and management principles, rather than just general knowledge or common sense.
Let's break down the knowledge required for the RAG and how you would go about crawling the web to acquire it.
"Your Idea Is Bullshit" App Design
Core Concept: A web application where users submit a startup idea, and an AI agent, powered by a RAG system, provides a harsh, evidence-based critique from business, marketing, and management perspectives.
Components:
Frontend (Web UI): Simple text input for the idea, a "Crush My Idea" button, and a display area for the LLM's detailed criticism.
Backend (Python/FastAPI/Flask):
Receives user input.
Triggers the RAG process.
Sends augmented prompt to the LLM.
Returns LLM's response to the frontend.
RAG System:
Knowledge Base (Vector Database): Stores embedded chunks of crawled business, marketing, and management content.
Retriever: Queries the knowledge base to find relevant information based on the user's startup idea.
Augmenter: Combines the retrieved information with the user's idea and a specific prompt for the LLM.
LLM Agent: Receives the augmented prompt and generates the harsh critique.
Web Crawler (Python/Playwright): Collects the raw HTML content for the RAG knowledge base.

1. Knowledge Required for the RAG System
To provide truly insightful and harsh criticism, your RAG system needs access to a wide array of structured and unstructured business knowledge. Here's a comprehensive list:
A. Business Strategy & Models:
Business Model Frameworks:
Business Model Canvas: Key Partners, Key Activities, Key Resources, Value Propositions, Customer Relationships, Channels, Customer Segments, Cost Structure, Revenue Streams.
Value Proposition Canvas: Customer Jobs, Pains, Gains, Products & Services, Pain Relievers, Gain Creators.
Lean Startup Methodology: MVP (Minimum Viable Product), Build-Measure-Learn loop, validated learning, pivot vs. persevere.
Strategic Analysis:
SWOT Analysis: Strengths, Weaknesses, Opportunities, Threats (internal/external).
Porter's Five Forces: Threat of new entrants, bargaining power of buyers, bargaining power of suppliers, threat of substitute products or services, rivalry among existing competitors.
PESTEL Analysis: Political, Economic, Social, Technological, Environmental, Legal factors impacting a business.
Competitive Advantage: Cost leadership, differentiation, niche focus.
Market Analysis:
TAM, SAM, SOM: Total Addressable Market, Serviceable Available Market, Serviceable Obtainable Market.
Market Sizing Techniques: Top-down, bottom-up, value chain analysis.
Market Trends: Emerging industries, declining industries, demographic shifts.
Financial Fundamentals (High-level):
Unit economics, customer acquisition cost (CAC), lifetime value (LTV).
Burn rate, runway, profitability, break-even analysis.
Funding stages (pre-seed, seed, Series A, etc.) and what investors look for.
B. Marketing & Sales:
Customer Acquisition:
Channels (digital, traditional, partnerships).
Conversion funnels.
Lead generation strategies.
Branding & Positioning:
Unique Selling Proposition (USP).
Target audience definition.
Brand messaging and storytelling.
Product-Market Fit: Understanding what it means and how to achieve/fail it.
Pricing Strategies: Cost-plus, value-based, competitive, freemium, subscription.
Sales Funnel: Awareness, Interest, Desire, Action (AIDA) or similar models.
Growth Hacking: Techniques for rapid growth, often low-cost and unconventional.
C. Management & Operations:
Team Building: Importance of co-founders, skill gaps, hiring challenges.
Execution Risk: Common operational pitfalls, supply chain issues, regulatory hurdles.
Scalability Challenges: How operations break down at scale, infrastructure needs.
Legal & Compliance (Basics): Intellectual property, data privacy (GDPR, CCPA), industry-specific regulations, common startup legal mistakes.
Product Development Lifecycle: Iterative development, user feedback loops.
D. Case Studies & Common Pitfalls:
Startup Failure Post-mortems: Real-world examples of why startups failed (e.g., lack of market need, run out of cash, not the right team, get outcompeted, pricing/cost issues).
Success Stories (with critical analysis): What made successful companies thrive, but also what challenges they overcame or almost succumbed to.
Cognitive Biases: Overconfidence, confirmation bias, sunk cost fallacy in entrepreneurship.

2. How to Crawl the Web to Get Such Knowledge
This is where your Playwright-based web crawling code comes in handy. You'll need a systematic approach to target high-quality sources and extract relevant information.
A. Identify High-Quality Sources (Seed URLs):
Start with authoritative sources to ensure the quality of your knowledge base.
Academic & Research:
Harvard Business Review (HBR): hbr.org (articles on strategy, management, marketing).
Stanford Graduate School of Business (GSB): gsb.stanford.edu (research, articles).
MIT Sloan Management Review: sloanreview.mit.edu (articles on innovation, technology management).
Wharton Knowledge@Wharton: knowledge.wharton.upenn.edu (articles, interviews).
Startup & VC Ecosystem:
Y Combinator (Startup School, Blog): ycombinator.com/library, blog.ycombinator.com (practical advice, common mistakes, founder stories, investment criteria).
Andreessen Horowitz (a16z) Blog: a16z.com/category/future-of-startup (VC perspective, market trends).
Sequoia Capital Insights: sequoiacap.com/insights (investment philosophy, market insights).
TechCrunch: techcrunch.com (startup news, analysis, funding rounds - filter for analysis pieces).
Business News & Analysis:
Forbes: forbes.com/business (articles, analysis).
Bloomberg Businessweek: bloomberg.com/businessweek (deep dives, industry analysis).
Inc. Magazine: inc.com (entrepreneurship, small business advice).
Entrepreneur.com: entrepreneur.com (startup advice, guides).
Specialized Resources:
Investopedia: investopedia.com (definitions of financial and business terms).
MarketingProfs: marketingprofs.com (marketing strategies, best practices).
HubSpot Blog: blog.hubspot.com (inbound marketing, sales, CRM).
