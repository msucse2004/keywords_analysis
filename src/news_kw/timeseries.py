"""Time series analysis for keywords."""

from pathlib import Path
import pandas as pd
from news_kw.config import Config


def create_timeseries(tokens_df: pd.DataFrame, keyword_topk: pd.DataFrame, 
                     config: Config, exclude_keywords: list, output_dir: Path) -> pd.DataFrame:
    """Create time series table for top keywords.
    
    Args:
        tokens_df: DataFrame with columns: doc_id, date, token
        keyword_topk: DataFrame with top keywords (token, freq)
        config: Configuration object
        exclude_keywords: List of keywords to exclude
        output_dir: Directory to save output table
        
    Returns:
        DataFrame with columns: date, token, freq, freq_norm
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter out excluded keywords (case-insensitive)
    exclude_set = set()
    if exclude_keywords:
        exclude_set = {kw.lower() for kw in exclude_keywords}
        tokens_df = tokens_df[~tokens_df['token'].str.lower().isin(exclude_set)].copy()
        # Also filter keyword_topk
        keyword_topk = keyword_topk[~keyword_topk['token'].str.lower().isin(exclude_set)].copy()
    
    # Get top N tokens
    top_tokens = set(keyword_topk['token'].head(config.KEYWORD_TOP_N))
    
    # Filter tokens to top N only
    filtered_tokens = tokens_df[tokens_df['token'].isin(top_tokens)].copy()
    
    # Convert date to datetime and then to monthly period
    filtered_tokens['date'] = pd.to_datetime(filtered_tokens['date'])
    filtered_tokens['month'] = filtered_tokens['date'].dt.to_period('M')
    
    # Group by month and token (aggregate by month)
    timeseries = filtered_tokens.groupby(['month', 'token']).size().reset_index(name='freq')
    
    # Get monthly date range (convert tokens_df date to datetime first)
    tokens_df_date = pd.to_datetime(tokens_df['date'])
    date_range = pd.period_range(
        start=tokens_df_date.min().to_period('M'),
        end=tokens_df_date.max().to_period('M'),
        freq='M'
    )
    
    # Create full month-token grid
    date_token_grid = pd.MultiIndex.from_product(
        [date_range, top_tokens],
        names=['month', 'token']
    ).to_frame(index=False)
    
    # Merge with actual frequencies
    timeseries_full = date_token_grid.merge(
        timeseries,
        on=['month', 'token'],
        how='left'
    ).fillna(0)
    
    # Calculate normalized frequency (per month)
    date_totals = timeseries_full.groupby('month')['freq'].transform('sum')
    timeseries_full['freq_norm'] = timeseries_full['freq'] / date_totals.replace(0, 1)
    
    # Convert month period to string format (YYYY-MM) for CSV
    timeseries_full['date'] = timeseries_full['month'].astype(str)
    
    # Remove month column, keep only date
    timeseries_full = timeseries_full.drop(columns=['month'])
    
    # Sort
    timeseries_full = timeseries_full.sort_values(['date', 'token']).reset_index(drop=True)
    
    # Save
    output_path = output_dir / 'keyword_timeseries.csv'
    timeseries_full.to_csv(output_path, index=False)
    
    return timeseries_full


def create_topn_by_date(timeseries_df: pd.DataFrame, config: Config, exclude_keywords: list, output_dir: Path) -> pd.DataFrame:
    """Create table with Top N keywords for each date.
    
    Args:
        timeseries_df: DataFrame with columns: date, token, freq, freq_norm
        config: Configuration object
        exclude_keywords: List of keywords to exclude
        output_dir: Directory to save output table
        
    Returns:
        DataFrame with columns: date, rank, token, freq, freq_norm
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert date string to period for monthly aggregation
    # Date format is YYYY-MM (monthly)
    timeseries_df['date'] = pd.to_datetime(timeseries_df['date']).dt.to_period('M')
    
    # Filter out excluded keywords (case-insensitive)
    exclude_set = set()
    if exclude_keywords:
        exclude_set = {kw.lower() for kw in exclude_keywords}
        timeseries_df = timeseries_df[~timeseries_df['token'].str.lower().isin(exclude_set)].copy()
    
    # For each month, get Top N keywords by frequency
    topn_by_date_list = []
    
    for date in sorted(timeseries_df['date'].unique()):
        date_data = timeseries_df[timeseries_df['date'] == date].copy()
        # Filter out zero frequencies
        date_data = date_data[date_data['freq'] > 0]
        # Filter out excluded keywords again (safety check)
        if exclude_set:
            date_data = date_data[~date_data['token'].str.lower().isin(exclude_set)].copy()
        if len(date_data) == 0:
            continue
        # Sort by frequency descending and take Top N
        top_n = date_data.nlargest(config.TREND_PLOT_TOP_N, 'freq')
        
        # Ensure we always have TREND_PLOT_TOP_N ranks
        # If we have fewer keywords than TREND_PLOT_TOP_N, repeat the last keyword
        if len(top_n) < config.TREND_PLOT_TOP_N:
            # Get the last row (lowest frequency keyword we have)
            last_row = top_n.iloc[-1].copy() if len(top_n) > 0 else None
            if last_row is not None:
                # Repeat the last keyword to fill up to TREND_PLOT_TOP_N
                rows_to_add = config.TREND_PLOT_TOP_N - len(top_n)
                additional_rows = pd.DataFrame([last_row] * rows_to_add)
                top_n = pd.concat([top_n, additional_rows], ignore_index=True)
        
        # Add rank column (always 1 to TREND_PLOT_TOP_N)
        top_n['rank'] = range(1, len(top_n) + 1)
        # Ensure we only keep exactly TREND_PLOT_TOP_N rows
        top_n = top_n.head(config.TREND_PLOT_TOP_N)
        topn_by_date_list.append(top_n)
    
    # Check if we have any data to concatenate
    if len(topn_by_date_list) == 0:
        # Return empty DataFrame with correct columns
        empty_df = pd.DataFrame(columns=['date', 'rank', 'token', 'freq', 'freq_norm'])
        output_path = output_dir / 'keyword_topn_by_date.csv'
        empty_df.to_csv(output_path, index=False)
        return empty_df
    
    # Combine all dates
    if len(topn_by_date_list) == 0:
        # Return empty DataFrame with correct columns if no data
        topn_by_date = pd.DataFrame(columns=['date', 'rank', 'token', 'freq', 'freq_norm'])
    else:
        topn_by_date = pd.concat(topn_by_date_list, ignore_index=True)
        # Reorder columns: date, rank, token, freq, freq_norm
        topn_by_date = topn_by_date[['date', 'rank', 'token', 'freq', 'freq_norm']]
        
        # Final safety check: filter out excluded keywords one more time
        if exclude_keywords:
            exclude_set = {kw.lower() for kw in exclude_keywords}
            topn_by_date = topn_by_date[~topn_by_date['token'].str.lower().isin(exclude_set)].copy()
        
        # Convert date period to string format (YYYY-MM) for CSV
        topn_by_date['date'] = topn_by_date['date'].astype(str)
        
        # Sort by date and rank
        topn_by_date = topn_by_date.sort_values(['date', 'rank']).reset_index(drop=True)
    
    # Save
    output_path = output_dir / 'keyword_topn_by_date.csv'
    topn_by_date.to_csv(output_path, index=False)
    
    return topn_by_date

