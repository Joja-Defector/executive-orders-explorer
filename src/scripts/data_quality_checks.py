#!/usr/bin/env python

"""
Data Quality Check Script for Executive Orders Scraper
This script performs quality checks on scraped executive order data.
"""

import os
import sys
import logging
import pandas as pd
import re
from datetime import datetime
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("eo_data_quality")

def load_data(filename='data/presidential_actions_with_content.csv'):
    """Load the scraped data file"""
    try:
        if not os.path.exists(filename):
            logger.error(f"File not found: {filename}")
            return None
            
        logger.info(f"Loading data from {filename}")
        df = pd.read_csv(filename)
        logger.info(f"Loaded {len(df)} records")
        return df
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None

def check_missing_values(df):
    """Check for missing values in critical columns"""
    if df is None or df.empty:
        return False
        
    critical_columns = ['title', 'link', 'date', 'content']
    missing_data = {}
    
    for column in critical_columns:
        if column not in df.columns:
            logger.error(f"Critical column missing: {column}")
            return False
            
        missing_count = df[column].isna().sum()
        missing_percentage = (missing_count / len(df)) * 100
        missing_data[column] = (missing_count, missing_percentage)
        
        if missing_percentage > 10:  # Alert if more than 10% of data is missing
            logger.warning(f"High missing data in '{column}': {missing_count} records ({missing_percentage:.1f}%)")
    
    logger.info("Missing value summary:")
    for col, (count, percentage) in missing_data.items():
        logger.info(f"  {col}: {count} missing values ({percentage:.1f}%)")
    
    # Check if any record has missing values in all critical fields
    complete_failures = df[critical_columns].isna().all(axis=1).sum()
    if complete_failures > 0:
        logger.error(f"Found {complete_failures} records with all critical fields missing")
        return False
        
    return True

def check_data_formats(df):
    """Check if data formats are as expected"""
    if df is None or df.empty:
        return False
        
    # Check URL format
    invalid_urls = 0
    url_pattern = re.compile(r'^https?://www\.whitehouse\.gov/.*$')
    
    for url in df['link']:
        if not isinstance(url, str) or not url_pattern.match(url):
            invalid_urls += 1
            
    if invalid_urls > 0:
        logger.warning(f"Found {invalid_urls} records with invalid URL format")
    
    # Check date format - expecting "DD-MMM-YY" or similar format
    invalid_dates = 0
    valid_dates = 0
    
    for date_str in df['date']:
        if not isinstance(date_str, str):
            invalid_dates += 1
            continue
            
        try:
            # Try different date formats
            date_formats = [
                "%d-%b-%y", "%d-%B-%y",  # 8-Apr-25, 8-April-25
                "%d-%b-%Y", "%d-%B-%Y",  # 8-Apr-2025, 8-April-2025
                "%d %b %y", "%d %B %y",  # 8 Apr 25, 8 April 25
                "%d %b %Y", "%d %B %Y",  # 8 Apr 2025, 8 April 2025
                "%B %d, %Y",             # April 8, 2025
                "%b %d, %Y",             # Apr 8, 2025
                "%Y-%m-%d"               # 2025-04-08
            ]
            
            success = False
            for fmt in date_formats:
                try:
                    datetime.strptime(date_str.strip(), fmt)
                    success = True
                    break
                except:
                    continue
                    
            if success:
                valid_dates += 1
            else:
                invalid_dates += 1
                
        except Exception:
            invalid_dates += 1
    
    if invalid_dates > 0:
        logger.warning(f"Found {invalid_dates} records with invalid date format")
    
    logger.info(f"Date format check: {valid_dates} valid, {invalid_dates} invalid")
    
    # Check content length
    short_content = df[df['content'].str.len() < 100].shape[0]
    if short_content > 0:
        logger.warning(f"Found {short_content} records with suspiciously short content (<100 chars)")
    
    # Check for error messages in content
    error_content = df[df['content'].str.contains('Error fetching content|No content found', case=False, na=False)].shape[0]
    if error_content > 0:
        logger.warning(f"Found {error_content} records with error messages in content")
    
    # Overall format check passes if major issues are below threshold
    format_errors = invalid_urls + invalid_dates + error_content
    threshold = len(df) * 0.1  # 10% threshold
    
    if format_errors > threshold:
        logger.error(f"Too many format errors: {format_errors} (threshold: {threshold:.0f})")
        return False
        
    return True

def check_duplicates(df):
    """Check for duplicate records"""
    if df is None or df.empty:
        return False
        
    # Check for exact duplicates
    exact_dupes = df.duplicated().sum()
    if exact_dupes > 0:
        logger.warning(f"Found {exact_dupes} exact duplicate records")
    
    # Check for duplicate links
    link_dupes = df.duplicated(subset=['link']).sum()
    if link_dupes > 0:
        logger.warning(f"Found {link_dupes} records with duplicate links")
    
    # Check for duplicate titles with different links
    title_groups = df.groupby('title')['link'].nunique()
    multi_link_titles = title_groups[title_groups > 1].shape[0]
    if multi_link_titles > 0:
        logger.warning(f"Found {multi_link_titles} titles with multiple different links")
    
    return exact_dupes == 0 and link_dupes == 0

def check_content_quality(df):
    """Check the quality of content data"""
    if df is None or df.empty:
        return False
        
    # Check content length distribution
    content_lengths = df['content'].str.len()
    avg_length = content_lengths.mean()
    min_length = content_lengths.min()
    max_length = content_lengths.max()
    
    logger.info(f"Content length stats: avg={avg_length:.0f}, min={min_length}, max={max_length}")
    
    # Flag very short content (might indicate scraping failure)
    very_short = df[content_lengths < 200].shape[0]
    if very_short > 0:
        logger.warning(f"Found {very_short} records with very short content (<200 chars)")
    
    # Check for potential HTML in content
    html_pattern = re.compile(r'<[a-z]+[^>]*>|</[a-z]+>')
    html_content = df[df['content'].str.contains(html_pattern, na=False)].shape[0]
    if html_content > 0:
        logger.warning(f"Found {html_content} records with potential HTML tags in content")
    
    # Check for excessive whitespace
    whitespace_pattern = re.compile(r'\n{3,}|\s{3,}')
    excessive_whitespace = df[df['content'].str.contains(whitespace_pattern, na=False)].shape[0]
    if excessive_whitespace > 0:
        logger.warning(f"Found {excessive_whitespace} records with excessive whitespace")
    
    # Calculate overall content quality score
    quality_issues = very_short + html_content
    threshold = len(df) * 0.15  # 15% threshold
    
    if quality_issues > threshold:
        logger.error(f"Too many content quality issues: {quality_issues} (threshold: {threshold:.0f})")
        return False
        
    return True

def check_recency(df):
    """Check if the data includes recent records"""
    if df is None or df.empty:
        return False
        
    try:
        # Sort the dataframe by date
        df['temp_date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Check if we have any valid dates
        if df['temp_date'].isna().all():
            logger.error("No valid dates found in the data")
            return False
            
        # Get the most recent date
        most_recent = df['temp_date'].max()
        today = datetime.now()
        days_diff = (today - most_recent).days
        
        logger.info(f"Most recent record is from {most_recent.strftime('%Y-%m-%d')} ({days_diff} days old)")
        
        # Alert if no recent data (adjust the threshold as needed)
        if days_diff > 14:  # Two weeks
            logger.warning(f"Data may be stale. Most recent record is {days_diff} days old")
        
        # Clean up temporary column
        df = df.drop(columns=['temp_date'])
        
        return days_diff <= 30  # Consider data fresh if within a month
        
    except Exception as e:
        logger.error(f"Error checking data recency: {e}")
        return False

def run_all_checks(filename='data/presidential_actions_with_content.csv'):
    """Run all data quality checks"""
    df = load_data(filename)
    
    if df is None or df.empty:
        logger.error("No data to check")
        return False
    
    logger.info(f"Running data quality checks on {len(df)} records")
    
    # Run all checks
    missing_check = check_missing_values(df)
    format_check = check_data_formats(df)
    duplicate_check = check_duplicates(df)
    content_check = check_content_quality(df)
    recency_check = check_recency(df)
    
    # Overall quality assessment
    checks_passed = sum([missing_check, format_check, duplicate_check, content_check, recency_check])
    total_checks = 5
    
    quality_score = (checks_passed / total_checks) * 100
    
    logger.info(f"Data quality score: {quality_score:.1f}% ({checks_passed}/{total_checks} checks passed)")
    
    # Check if quality is acceptable
    if quality_score >= 80:
        logger.info("DATA QUALITY ACCEPTABLE")
        return True
    else:
        logger.error("DATA QUALITY UNACCEPTABLE - review warnings")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run data quality checks on scraped EO data')
    parser.add_argument('--file', type=str, default='data/presidential_actions_with_content.csv',
                       help='Path to the CSV file to check')
    parser.add_argument('--fail-on-errors', action='store_true',
                       help='Exit with non-zero code if quality checks fail')
    
    args = parser.parse_args()
    
    # Run checks
    checks_passed = run_all_checks(args.file)
    
    # Exit with appropriate code
    if not checks_passed and args.fail_on_errors:
        sys.exit(1)