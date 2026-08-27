import os
import re
from tavily import AsyncTavilyClient

def clean_content(text: str, max_length: int = 3000) -> str:
    """
    Cleans extracted markdown/text content:
    1. Removes markdown images entirely: ![alt](url)
    2. Replaces markdown links with link text: [text](url) -> text
    3. Removes social-media/boilerplate lines.
    4. Removes empty lines.
    5. Limits content to max_length while preserving sentence integrity if possible.
    """
    if not text:
        return ""
        
    # Remove markdown images entirely: ![alt](url)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    
    # Replace markdown links with just their text: [link text](url) -> link text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Split text into lines
    lines = text.split('\n')
    cleaned_lines = []
    
    # Common social media/boilerplate keywords
    boilerplate_keywords = {
        'share this', 'follow us', 'facebook', 'twitter', 'linkedin', 
        'instagram', 'youtube', 'subscribe', 'newsletter', 'sign up', 
        'privacy policy', 'terms of service', 'all rights reserved', 
        'copyright ©', 'cookie policy', 'click here', 'read more'
    }
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
            
        # Check if line is likely boilerplate
        line_lower = line_strip.lower()
        if any(keyword in line_lower for keyword in boilerplate_keywords):
            # Skip if it is short boilerplate
            if len(line_strip) < 120:
                continue
                
        cleaned_lines.append(line_strip)
        
    # Reconstruct clean text with newlines
    cleaned_text = '\n'.join(cleaned_lines)
    
    # Limit content length
    if len(cleaned_text) > max_length:
        truncated = cleaned_text[:max_length]
        last_period = truncated.rfind('.')
        # If there's a period near the end, cut there to preserve sentence boundary
        if last_period > max_length * 0.8:
            cleaned_text = truncated[:last_period + 1]
        else:
            cleaned_text = truncated + "..."
            
    return cleaned_text

async def search_web(query: str) -> list[dict[str, str]]:
    """
    Search the web using Tavily Async API Client.
    Reads the Tavily API Key from TAVILY_API_KEY environment variable.
    Extracts the clean markdown/text content from the top 3 results using Tavily's extract API.
    
    Args:
        query: The search query string.
        
    Returns:
        A list of dictionaries containing title, url, and cleaned content for each result.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable is not set")
    
    client = AsyncTavilyClient(api_key=api_key)
    response = await client.search(query=query)
    
    results = response.get("results", [])
    
    # Extract top 3 URLs
    top_results = results[:3]
    top_urls = [r.get("url") for r in top_results if r.get("url")]
    
    extracted_map = {}
    if top_urls:
        try:
            # Retrieve content from URLs using Tavily Extract
            extract_resp = await client.extract(urls=top_urls)
            for item in extract_resp.get("results", []):
                url = item.get("url")
                raw_content = item.get("raw_content")
                if url and raw_content:
                    extracted_map[url] = raw_content
        except Exception:
            # Fallback to search result snippet if extraction fails
            pass
            
    formatted_results = [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            # Clean content using the clean_content helper
            "content": clean_content(
                extracted_map.get(result.get("url", ""), result.get("content", ""))
            )
        }
        for result in results
    ]
    
    return formatted_results
