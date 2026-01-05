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
    
    # Group by date and token
    timeseries = filtered_tokens.groupby(['date', 'token']).size().reset_index(name='freq')
    
    # Get date range
    date_range = pd.date_range(
        start=tokens_df['date'].min(),
        end=tokens_df['date'].max(),
        freq='D'
    )
    
    # Create full date-token grid
    date_token_grid = pd.MultiIndex.from_product(
        [date_range, top_tokens],
        names=['date', 'token']
    ).to_frame(index=False)
    
    # Merge with actual frequencies
    timeseries_full = date_token_grid.merge(
        timeseries,
        on=['date', 'token'],
        how='left'
    ).fillna(0)
    
    # Calculate normalized frequency (per date)
    date_totals = timeseries_full.groupby('date')['freq'].transform('sum')
    timeseries_full['freq_norm'] = timeseries_full['freq'] / date_totals.replace(0, 1)
    
    # Sort
    timeseries_full = timeseries_full.sort_values(['date', 'token']).reset_index(drop=True)
    
    # Convert date to string for CSV
    timeseries_full['date'] = timeseries_full['date'].dt.strftime('%Y-%m-%d')
    
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
    
    # Convert date back to datetime for sorting
    timeseries_df['date'] = pd.to_datetime(timeseries_df['date'])
    
    # Filter out excluded keywords (case-insensitive)
    exclude_set = set()
    if exclude_keywords:
        exclude_set = {kw.lower() for kw in exclude_keywords}
        timeseries_df = timeseries_df[~timeseries_df['token'].str.lower().isin(exclude_set)].copy()
    
    # For each date, get Top N keywords by frequency
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
        # Add rank column
        top_n['rank'] = range(1, len(top_n) + 1)
        topn_by_date_list.append(top_n)
    
    # Check if we have any data to concatenate
    if len(topn_by_date_list) == 0:
        # Return empty DataFrame with correct columns
        empty_df = pd.DataFrame(columns=['date', 'rank', 'token', 'freq', 'freq_norm'])
        output_path = output_dir / 'keyword_topn_by_date.csv'
        empty_df.to_csv(output_path, index=False)
        return empty_df
    
    # Combine all dates
    topn_by_date = pd.concat(topn_by_date_list, ignore_index=True)
    
    # Reorder columns: date, rank, token, freq, freq_norm
    topn_by_date = topn_by_date[['date', 'rank', 'token', 'freq', 'freq_norm']]
    
    # Final safety check: filter out excluded keywords one more time
    if exclude_keywords:
        exclude_set = {kw.lower() for kw in exclude_keywords}
        topn_by_date = topn_by_date[~topn_by_date['token'].str.lower().isin(exclude_set)].copy()
    
    # Convert date to string for CSV
    topn_by_date['date'] = topn_by_date['date'].dt.strftime('%Y-%m-%d')
    
    # Sort by date and rank
    topn_by_date = topn_by_date.sort_values(['date', 'rank']).reset_index(drop=True)
    
    # Save
    output_path = output_dir / 'keyword_topn_by_date.csv'
    topn_by_date.to_csv(output_path, index=False)
    
    return topn_by_date

