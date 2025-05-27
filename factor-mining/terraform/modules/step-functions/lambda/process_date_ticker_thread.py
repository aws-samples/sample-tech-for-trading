import json
import logging
import os
import re
import math
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logger.setLevel(getattr(logging, log_level))

def divide_date_range(start_date_obj, end_date_obj, num_segments):
    """
    Divide a date range into equal segments.
    
    Args:
        start_date_obj: Start date as datetime object
        end_date_obj: End date as datetime object
        num_segments: Number of segments to divide the range into
        
    Returns:
        List of tuples containing (start_date, end_date) for each segment
    """
    total_days = (end_date_obj - start_date_obj).days
    
    # If total days is less than num_segments, adjust num_segments
    if total_days < num_segments:
        num_segments = total_days
        logger.warning(f"Adjusted thread_no to {num_segments} as there are only {total_days} days in the range")
    
    # Calculate days per segment (might have remainder)
    days_per_segment = total_days / num_segments
    
    segments = []
    for i in range(num_segments):
        segment_start = start_date_obj + timedelta(days=int(i * days_per_segment))
        
        # For the last segment, use the original end_date to avoid rounding issues
        if i == num_segments - 1:
            segment_end = end_date_obj
        else:
            segment_end = start_date_obj + timedelta(days=int((i + 1) * days_per_segment) - 1)
        
        segments.append({
            "start_date": segment_start.strftime('%Y-%m-%d'),
            "end_date": segment_end.strftime('%Y-%m-%d')
        })
    
    return segments

def divide_tickers_into_groups(tickers_list, parallel_m):
    """
    Divide a list of tickers into parallel_m groups for parallel processing.
    
    Args:
        tickers_list: List of ticker symbols
        parallel_m: Number of groups to divide the tickers into
        
    Returns:
        List of ticker groups, each containing a subset of tickers
    """
    # Ensure parallel_m is at least 1
    parallel_m = max(1, parallel_m)
    
    # If parallel_m is greater than the number of tickers, adjust it
    if parallel_m > len(tickers_list):
        parallel_m = len(tickers_list)
        logger.warning(f"Adjusted parallel_M to {parallel_m} as there are only {len(tickers_list)} tickers")
    
    # Calculate tickers per group (might have remainder)
    tickers_per_group = math.ceil(len(tickers_list) / parallel_m)
    
    ticker_groups = []
    for i in range(0, len(tickers_list), tickers_per_group):
        group = tickers_list[i:i + tickers_per_group]
        ticker_groups.append(','.join(group))
    
    logger.info(f"Divided {len(tickers_list)} tickers into {len(ticker_groups)} groups")
    return ticker_groups

def prepare_ticker_jobs(event):
    """
    Prepare ticker jobs for individual ticker processing.
    
    Args:
        event: Event containing start_date, end_date, tickers, and other parameters
        
    Returns:
        Dictionary with tickerJobs array and other parameters
    """
    try:
        start_date = event.get('start_date')
        end_date = event.get('end_date')
        tickers_str = event.get('tickers')
        thread_no = event.get('thread_no', 1)
        parallel_m = int(event.get('parallel_m', 1))  # Default to 1 if not provided
        factor = event.get('factor', 'DE')  # Default to 'DE' if not provided
        date_range_results = event.get('dateRangeResults', [])
        
        # Parse tickers string to get individual tickers
        if isinstance(tickers_str, str):
            tickers_list = [ticker.strip() for ticker in tickers_str.split(',')]
        else:
            raise ValueError("Tickers must be a comma-separated string")
        
        # Always divide tickers into groups based on parallel_m
        # If parallel_m is 1, each ticker will be its own group
        ticker_groups = divide_tickers_into_groups(tickers_list, parallel_m)
        
        # Create ticker group jobs
        ticker_jobs = []
        for i, group in enumerate(ticker_groups):
            ticker_jobs.append({
                "ticker_group": group,
                "start_date": start_date,
                "end_date": end_date,
                "factor": factor,
                "group_index": i
            })
        
        logger.info(f"Prepared {len(ticker_jobs)} ticker group jobs for processing")
        
        result = {
            "original_start_date": start_date,
            "original_end_date": end_date,
            "tickers": tickers_str,
            "thread_no": thread_no,
            "parallel_m": parallel_m,
            "factor": factor,
            "dateRangeResults": date_range_results,
            "tickerJobs": ticker_jobs
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error preparing ticker jobs: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Process input with start_date, end_date, tickers, thread_no, and parallel_m.
    Divides the date range into thread_no segments for parallel processing.
    Divides tickers into parallel_m groups for parallel processing.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Check if this is a prepare_ticker_jobs operation
        operation = event.get('operation')
        if operation == 'prepare_ticker_jobs':
            return prepare_ticker_jobs(event)
        
        # Extract and validate input parameters
        start_date = event.get('start_date')
        end_date = event.get('end_date')
        tickers_str = event.get('tickers')
        thread_no = int(event.get('thread_no', 1))
        parallel_m = int(event.get('parallel_m', 1))  # Default to 1 if not provided
        factor = event.get('factor', 'DE')  # Default to 'DE' if not provided
        
        # Validate date format (yyyy-mm-dd)
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if not date_pattern.match(start_date) or not date_pattern.match(end_date):
            raise ValueError("Dates must be in yyyy-mm-dd format")
        
        # Parse dates
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Check that end_date is later than start_date
        if end_date_obj <= start_date_obj:
            raise ValueError(f"End date ({end_date}) must be later than start date ({start_date})")
        
        # Keep tickers in original format (don't convert to array)
        if isinstance(tickers_str, str):
            tickers = tickers_str  # Keep as comma-separated string
        elif isinstance(tickers_str, list):
            tickers = ','.join(tickers_str)  # Convert list to comma-separated string
        else:
            raise ValueError("Tickers must be a comma-separated string or a list")
        
        # Validate thread_no
        if thread_no < 1:
            thread_no = 1
            logger.warning("thread_no was less than 1, defaulting to 1")
            
        # Validate parallel_m
        if parallel_m < 1:
            parallel_m = 1
            logger.warning("parallel_m was less than 1, defaulting to 1")
        
        # Divide the date range into thread_no segments
        date_segments = divide_date_range(start_date_obj, end_date_obj, thread_no)
        
        # Create batch job parameters for each segment
        batch_jobs = []
        for i, segment in enumerate(date_segments):
            batch_jobs.append({
                "start_date": segment["start_date"],
                "end_date": segment["end_date"],
                "tickers": tickers,  # Use the original tickers string, not a list
                "factor": factor,
                "index": i
            })
        
        result = {
            "original_start_date": start_date,
            "original_end_date": end_date,
            "tickers": tickers,  # Keep as comma-separated string
            "thread_no": thread_no,
            "parallel_m": parallel_m,  # Include parallel_m in the result
            "factor": factor,  # Include factor in the result
            "date_segments": date_segments,
            "batch_jobs": batch_jobs,
            "result": {
                "status": "processed",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }
        
        logger.info(f"Processed input with tickers: {tickers} and divided into {len(date_segments)} date segments")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing input: {str(e)}")
        raise
