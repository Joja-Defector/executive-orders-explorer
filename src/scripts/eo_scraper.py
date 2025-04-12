#!/usr/bin/env python

"""
This script was automatically generated from eo_webscraper.ipynb
for use in GitHub Actions workflow.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("eo_scraper")

# Cell:
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import os
import re

def load_existing_data(filename='data/presidential_actions_with_content.csv'):
    """Load existing data or return an empty DataFrame if the file doesn't exist"""
    if os.path.exists(filename):
        try:
            print(f"Loading existing data from {filename}")
            # Read CSV but specify date column as object (string) to prevent automatic conversion
            df = pd.read_csv(filename, dtype={'date': str})
            print(f"Found {len(df)} existing entries")
            return df
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return pd.DataFrame(columns=['title', 'link', 'date', 'page_number', 'content'])
    else:
        print("No existing data file found. Will create a new one.")
        return pd.DataFrame(columns=['title', 'link', 'date', 'page_number', 'content'])

def get_content(url, headers):
    """Helper function to get content from individual pages"""
    try:
        print(f"\nFetching content from: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Print the first part of the HTML for debugging
        print("HTML preview:")
        print(soup.prettify()[:500])
        
        # Try different content areas first
        content_area = (
            soup.select_one('main#main-content') or
            soup.select_one('.entry-content') or
            soup.select_one('.post-content') or
            soup.select_one('article')
        )
        
        if content_area:
            print("Found content area")
            paragraphs = content_area.find_all('p')
        else:
            print("No specific content area found, searching all paragraphs")
            paragraphs = soup.find_all('p')
        
        print(f"Found {len(paragraphs)} paragraphs")
        
        # Print the first paragraph for debugging
        if paragraphs:
            print("First paragraph preview:")
            print(paragraphs[0])
        
        if paragraphs:
            # Filter out empty paragraphs and join with newlines
            content_paragraphs = [p.text.strip() for p in paragraphs if p.text.strip()]
            print(f"Number of non-empty paragraphs: {len(content_paragraphs)}")
            
            if content_paragraphs:
                content = '\n'.join(content_paragraphs)
                print(f"Content preview: {content[:200]}...")
                return content
            
        print("No paragraphs found with content")
        return "No content found"
        
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        print(f"Response status: {response.status_code if 'response' in locals() else 'No response'}")
        return "Error fetching content"
    
def detect_total_pages(base_url, headers):
    """Detect the total number of pages available for scraping from WordPress block editor pagination"""
    try:
        print("Detecting total number of pages...")
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the specific block editor pagination element
        pagination = soup.select_one('nav.wp-block-query-pagination')
        
        if pagination:
            # Find all page number elements with data-wp-key attributes
            page_elements = pagination.find_all('a', attrs={'data-wp-key': lambda x: x and x.startswith('index-')})
            
            # Extract the page numbers from URLs or elements
            page_numbers = []
            for link in page_elements:
                # Try to find page number in the URL
                if 'href' in link.attrs:
                    match = re.search(r'/page/(\d+)', link['href'])
                    if match:
                        page_numbers.append(int(match.group(1)))
                        continue
                
                # Get the displayed text which is likely the page number
                if link.text and link.text.strip().isdigit():
                    page_numbers.append(int(link.text.strip()))
                    continue
                    
                # Try to extract from data-wp-key attribute
                if 'data-wp-key' in link.attrs:
                    key_match = re.search(r'index-(\d+)', link['data-wp-key'])
                    if key_match:
                        # Add 1 because index is 0-based but page numbers are 1-based
                        page_numbers.append(int(key_match.group(1)) + 1)
            
            if page_numbers:
                max_page = max(page_numbers)
                print(f"Detected {max_page} pages from block editor pagination")
                return max_page
            
            # Check the last link which might go to the last page
            last_link = pagination.select_one('a[data-wp-key="query-pagination-next"]')
            if last_link and 'href' in last_link.attrs:
                match = re.search(r'/page/(\d+)', last_link['href'])
                if match:
                    next_page = int(match.group(1))
                    # Since this is "next", the total pages is at least this value
                    print(f"Detected at least {next_page} pages from 'Next' link")
                    return next_page
        
        # If we couldn't find it through the main pagination component, look for the highest page link anywhere
        page_links = soup.find_all('a', href=True)
        page_numbers = []
        for link in page_links:
            match = re.search(r'/page/(\d+)', link['href'])
            if match:
                page_numbers.append(int(match.group(1)))
        
        if page_numbers:
            max_page = max(page_numbers)
            print(f"Detected {max_page} pages from page links")
            return max_page
            
        # There's a specific pattern in the HTML you provided with data-wp-key="index-X"
        # Let's try to find the highest index
        index_elements = soup.find_all(attrs={'data-wp-key': lambda x: x and x.startswith('index-')})
        if index_elements:
            indices = []
            for element in index_elements:
                key_match = re.search(r'index-(\d+)', element['data-wp-key'])
                if key_match:
                    indices.append(int(key_match.group(1)))
            
            if indices:
                # The highest index + 1 is the number of pages (since indices are 0-based)
                max_page = max(indices) + 1
                print(f"Detected {max_page} pages from index attributes")
                return max_page
        
        print("Could not detect total pages, defaulting to 1 page")
        return 1
        
    except Exception as e:
        print(f"Error detecting total pages: {e}")
        print("Defaulting to 1 page")
        return 1

def scrape_whitehouse_actions(num_pages=None, existing_df=None):
    base_url = "https://www.whitehouse.gov/presidential-actions/"
    all_actions = []
    existing_links = set()
    new_items_count = 0
    
    if existing_df is not None and not existing_df.empty:
        existing_links = set(existing_df['link'].tolist())
        print(f"Loaded {len(existing_links)} existing links to check against")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    # Auto-detect number of pages if not provided
    if num_pages is None:
        num_pages = detect_total_pages(base_url, headers)
    
    for page in range(1, num_pages + 1):
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        print(f"\nScraping page {page}: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            print(f"Response status code: {response.status_code}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            items = (
                soup.select('article.news-item') or 
                soup.select('.news-item') or 
                soup.select('article') or
                soup.select('.post')
            )
            
            print(f"\nFound {len(items)} items on this page")
            
            if not items:
                print("No items found. This might be the last page.")
                break
            
            for item in items:
                try:
                    title_elem = (
                        item.select_one('.news-item__title') or
                        item.select_one('h2 a') or
                        item.select_one('h3 a') or
                        item.select_one('.entry-title a')
                    )
                    
                    date_elem = (
                        item.select_one('.news-item__date') or
                        item.select_one('.entry-date') or
                        item.select_one('time')
                    )
                    
                    title = title_elem.text.strip() if title_elem else "No title"
                    link = title_elem['href'] if title_elem and title_elem.get('href') else "No link"
                    
                    # Skip if this link already exists in our dataset
                    if link in existing_links:
                        print(f"Skipping already collected item: {title[:50]}...")
                        continue
                    
                    # Get the date directly from the element
                    date_str = date_elem.text.strip() if date_elem else "No date"
                    
                    # Get content from the individual page
                    print(f"Fetching content for: {title[:50]}...")
                    content = get_content(link, headers) if link != "No link" else "No content"
                    
                    action = {
                        'title': title,
                        'link': link,
                        'date': date_str,
                        'page_number': page,
                        'content': content
                    }
                    all_actions.append(action)
                    new_items_count += 1
                    print(f"Processed: {title[:50]}...")
                    print(f"Date captured: {date_str}")
                    
                    # Add a small delay between content requests
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error processing item: {e}")
            
        except requests.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            break
        
        time.sleep(2)  # Delay between pages
    
    # Create DataFrame from newly scraped actions
    new_df = pd.DataFrame(all_actions)
    
    # If we have existing data and new data, combine them
    if existing_df is not None and not existing_df.empty and not new_df.empty:
        # Make a clean copy of the existing dataframe
        combined_df = existing_df.copy()
        
        # Simply append the new records 
        combined_df = pd.concat([combined_df, new_df], ignore_index=True)
        print(f"\nAdded {new_items_count} new items to the existing {len(existing_df)} items")
    elif not new_df.empty:
        combined_df = new_df
        print(f"\nCreated new dataset with {new_items_count} items")
    else:
        if existing_df is not None:
            combined_df = existing_df.copy()
            print("\nNo new items found, using existing data")
        else:
            combined_df = pd.DataFrame(columns=['title', 'link', 'date', 'page_number', 'content'])
            print("\nNo data found at all")
    
    # Process final dataframe
    if not combined_df.empty:
        # Create a temporary date column for sorting only
        try:
            # First make a copy of the date column as strings
            combined_df['sort_date'] = pd.to_datetime(combined_df['date'], errors='coerce')
            
            # Sort by the temporary date column
            combined_df = combined_df.sort_values('sort_date', ascending=False, na_position='last')
            
            # Remove the temporary sorting column
            combined_df = combined_df.drop(columns=['sort_date'])
        except Exception as e:
            print(f"Warning: Error in date sorting: {e}")
            # If sorting fails, still proceed with saving
        
        # Remove duplicates
        combined_df = combined_df.drop_duplicates(subset='link', keep='first')
        combined_df = combined_df.reset_index(drop=True)
        
        # Save to CSV
        filename = 'data/presidential_actions_with_content.csv'
        combined_df.to_csv(filename, index=False)
        print(f"\nData saved to '{filename}'")
        
        # Check for missing dates
        date_counts = combined_df['date'].isna().sum() if 'date' in combined_df.columns else 0
        print(f"Records with missing dates: {date_counts}")
    
    return combined_df

# Run the scraper
print("Starting data collection...")
existing_df = load_existing_data()
df = scrape_whitehouse_actions(existing_df=existing_df) 

if not df.empty:
    print("\nFirst few entries (showing truncated content):")
    # Show first few entries with truncated content
    preview_df = df.copy()
    if 'content' in preview_df.columns:
        preview_df['content'] = preview_df['content'].str[:200] + '...'
    print(preview_df[['title', 'date', 'link']].head())
    print(f"\nTotal items: {len(df)}")
    
    # Print some content statistics
    if 'content' in df.columns:
        print("\nContent statistics:")
        print(f"Average content length: {df['content'].str.len().mean():.0f} characters")
        print(f"Minimum content length: {df['content'].str.len().min()} characters")
        print(f"Maximum content length: {df['content'].str.len().max()} characters")
else:
    print("\nNo data collected")

if __name__ == "__main__":
    try:
        logger.info("Starting EO scraper script")
        # You can add command line argument handling here if needed
        # Main execution
        logger.info("EO scraper completed successfully")
    except Exception as e:
        logger.error(f"Error in EO scraper: {str(e)}")
        sys.exit(1)