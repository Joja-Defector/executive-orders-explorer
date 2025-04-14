import pandas as pd
import anthropic
import time
from datetime import datetime
import os
import argparse

def summarize_executive_order(client, content, title, date):
    """
    Send executive order content to Anthropic API and get a structured summary.
    
    Args:
        client: Anthropic API client
        content: The text content of the executive order
        title: The title of the executive order
        date: The date the executive order was issued
        
    Returns:
        String containing the formatted summary
    """
    prompt = f"""
You are analyzing an executive order titled "{title}" issued on {date}.

Here is the full text of the executive order:
---
{content}
---

Please provide a concise summary covering:
1. A simplified explanation of what this executive order is about (2-3 sentences)
2. Potential pros and cons of this order (2-3 bullet points each)
3. What it means and its potential impact (2-3 sentences)
4. Whether it appears lawful/constitutional or potentially overreaches executive power (1-2 sentences)

Format your response in a simple text format without any markdown or special formatting.
"""

    try:
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            temperature=0.0,
            system="You are an expert in law, government, and policy analysis. Your task is to analyze executive orders and provide concise, balanced summaries that help ordinary citizens understand them.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        return "Error generating summary."

def main():
    parser = argparse.ArgumentParser(description='Summarize executive orders using Anthropic API')
    parser.add_argument('--input', type=str, required=True, help='Path to input CSV file with new executive orders')
    parser.add_argument('--previous', type=str, help='Path to CSV file with previously summarized executive orders')
    parser.add_argument('--api-key', type=str, required=True, help='Anthropic API key')
    parser.add_argument('--output-dir', type=str, default='output', help='Directory to save output CSV')
    parser.add_argument('--unique-id', type=str, default='title', 
                       help='Column to use as unique identifier for executive orders (default: title)')
    parser.add_argument('--force-update', action='store_true',
                       help='Process all executive orders in the input file, overwriting any existing summaries')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get current date for filename
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_filename = f"{args.output_dir}/executive_orders_summarized_{current_date}.csv"
    
    print(f"Reading data from {args.input}...")
    
    # Read the input CSV file with new executive orders
    try:
        new_df = pd.read_csv(args.input)
        print(f"Loaded {len(new_df)} executive orders from input file.")
    except Exception as e:
        print(f"Error reading input CSV file: {e}")
        return
    
    # Check if required columns exist in new data
    required_columns = ['title', 'date', 'content']
    for col in required_columns:
        if col not in new_df.columns:
            print(f"Error: Required column '{col}' not found in input CSV.")
            return
    
    # Load previously summarized executive orders if provided
    if args.previous:
        try:
            prev_df = pd.read_csv(args.previous)
            print(f"Loaded {len(prev_df)} previously summarized executive orders.")
            
            # Check if summary column exists in previous data
            if 'summary' not in prev_df.columns:
                print(f"Warning: 'summary' column not found in previous CSV. File may not contain summaries.")
        except Exception as e:
            print(f"Error reading previous CSV file: {e}")
            return
    else:
        prev_df = pd.DataFrame(columns=new_df.columns.tolist() + ['summary'])
        print("No previous file provided. Will process all executive orders.")
    
    # Identify new executive orders that haven't been summarized yet
    unique_id = args.unique_id
    if unique_id not in new_df.columns:
        print(f"Error: Unique identifier column '{unique_id}' not found in input CSV.")
        return
    
    # Force update if flag is set
    if args.force_update:
        print("Force update flag is set. Will process all executive orders in the input file.")
        to_process_df = new_df.copy()
    elif prev_df.empty or unique_id not in prev_df.columns:
        # If no previous data or missing ID column, process all as new
        to_process_df = new_df.copy()
    else:
        # Find executive orders that are in the new file but not in the previous file
        # Clean and normalize the IDs for comparison
        new_df['_clean_id'] = new_df[unique_id].astype(str).str.strip()
        prev_df['_clean_id'] = prev_df[unique_id].astype(str).str.strip()
        
        # Convert to sets of strings to ensure consistent comparison
        previously_processed_ids = set(prev_df['_clean_id'])
        new_ids = set(new_df['_clean_id'])
        
        # Log the comparison for debugging
        print(f"Input file has {len(new_ids)} unique IDs")
        print(f"Previous file has {len(previously_processed_ids)} unique IDs")
        print(f"Difference: {len(new_ids - previously_processed_ids)} new IDs")
        
        # Create a mask for entries that need processing
        ids_to_process = new_ids - previously_processed_ids
        to_process_mask = new_df['_clean_id'].isin(ids_to_process)
        to_process_df = new_df[to_process_mask].copy()
        
        # Debug log
        print(f"Based on comparison, found {len(to_process_df)} new executive orders to process.")
        
        # If we found new IDs but to_process_df is empty, something went wrong
        if len(ids_to_process) > 0 and len(to_process_df) == 0:
            print("ERROR: Found new IDs but couldn't match them back to the dataframe.")
            print("This indicates a problem with the ID comparison.")
            print("Sample new IDs that couldn't be matched:", list(ids_to_process)[:3])
            print("Try using the --force-update flag to process all executive orders.")
    
    print(f"Found {len(to_process_df)} new executive orders to process.")
    
    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=args.api_key)
    
    # Add a new column for summaries
    to_process_df['summary'] = None
    
    # Process each new executive order
    for i, row in to_process_df.iterrows():
        print(f"Processing executive order {i-to_process_df.index[0]+1}/{len(to_process_df)}: {row[unique_id]}")
        
        # Skip if content is empty
        if pd.isna(row['content']) or row['content'].strip() == '':
            print("  Skipping - No content available")
            continue
        
        # Get summary from Anthropic API
        summary = summarize_executive_order(
            client, 
            row['content'], 
            row['title'], 
            row['date']
        )
        
        # Add summary to dataframe
        to_process_df.at[i, 'summary'] = summary
        
        # Print progress
        print(f"  Summary generated ({len(summary)} chars)")
        
        # Rate limiting to avoid hitting API limits
        if i < to_process_df.index[-1]:
            print("  Waiting 2 seconds before next request...")
            time.sleep(2)
    
    # Combine previous and new summaries
    if args.previous and not prev_df.empty:
        # Remove temporary _clean_id column if it exists
        if '_clean_id' in new_df.columns:
            new_df = new_df.drop(columns=['_clean_id'])
        if '_clean_id' in prev_df.columns:
            prev_df = prev_df.drop(columns=['_clean_id'])
        if '_clean_id' in to_process_df.columns:
            to_process_df = to_process_df.drop(columns=['_clean_id'])
            
        if to_process_df.empty:
            print("No new executive orders found to process.")
            
            # Check for any executive orders in the input that aren't in the previous file
            # This could happen if the unique ID comparison failed but there are legitimately new orders
            new_ids = set(new_df[unique_id].astype(str).str.strip())
            prev_ids = set(prev_df[unique_id].astype(str).str.strip())
            missing_ids = new_ids - prev_ids
            
            if missing_ids:
                print(f"Warning: Found {len(missing_ids)} executive orders in the input file that aren't in the previous file,")
                print("but they weren't processed. This may indicate an issue with the comparison logic.")
                print(f"First few missing IDs: {list(missing_ids)[:3]}")
            
            # Use the previous data as the result - PRESERVE ALL EXISTING COLUMNS AND VALUES
            result_df = prev_df.copy()
        else:
            # Only add necessary new columns from new_df to prev_df
            for col in to_process_df.columns:
                if col not in prev_df.columns:
                    prev_df[col] = None
                    
            # Only add necessary new columns from prev_df to to_process_df
            for col in prev_df.columns:
                if col not in to_process_df.columns:
                    to_process_df[col] = None
                
            # Concatenate the dataframes
            result_df = pd.concat([prev_df, to_process_df], ignore_index=True)
            
            # Drop duplicates based on the unique identifier, keeping the latest one (with summary)
            result_df = result_df.drop_duplicates(subset=[unique_id], keep='last')
    else:
        # Remove temporary _clean_id column if it exists
        if '_clean_id' in to_process_df.columns:
            to_process_df = to_process_df.drop(columns=['_clean_id'])
        result_df = to_process_df
    
    # Save the updated dataframe to a new CSV file
    try:
        result_df.to_csv(output_filename, index=False)
        print(f"\nSuccessfully saved {len(result_df)} executive orders to {output_filename}")
        print(f"  {len(to_process_df)} newly summarized")
        print(f"  {len(result_df) - len(to_process_df)} from previous file")
    except Exception as e:
        print(f"Error saving CSV file: {e}")

if __name__ == "__main__":
    main()