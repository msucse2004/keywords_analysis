"""Keyword lag analysis: Check if keywords from source groups appear later in target group."""

import pandas as pd
from pathlib import Path
from typing import Dict, List
import logging


logger = logging.getLogger(__name__)


def load_keyword_by_date(csv_path: Path) -> pd.DataFrame:
    """Load keyword_by_date.csv.
    
    Args:
        csv_path: Path to keyword_by_date.csv
        
    Returns:
        DataFrame with columns: date, token, freq
    """
    if not csv_path.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    return df


def get_monthly_topn_keywords(df: pd.DataFrame, top_n: int, exclude_keywords: List[str]) -> Dict[str, List[str]]:
    """Get Top N keywords for each month.
    
    Args:
        df: DataFrame with columns: date, token, freq
        top_n: Number of top keywords to select per month
        exclude_keywords: List of keywords to exclude
        
    Returns:
        Dict mapping month (YYYY-MM format) to list of top N keywords
    """
    # Filter out exclude keywords
    if exclude_keywords:
        exclude_set = {kw.lower() for kw in exclude_keywords}
        df = df[~df['token'].str.lower().isin(exclude_set)].copy()
    
    # Add year-month column
    df['year_month'] = df['date'].dt.to_period('M').astype(str)
    
    # For each month, get Top N keywords by frequency
    monthly_topn = {}
    
    for month in sorted(df['year_month'].unique()):
        month_data = df[df['year_month'] == month].copy()
        
        # Aggregate frequency by token for this month
        token_freq = month_data.groupby('token')['freq'].sum().reset_index()
        token_freq = token_freq.sort_values('freq', ascending=False)
        
        # Get Top N
        top_tokens = token_freq.head(top_n)['token'].tolist()
        monthly_topn[month] = top_tokens
    
    return monthly_topn


def analyze_keyword_lag_monthly(source_groups: List[str], target_group: str, 
                                top_n: int, exclude_keywords: List[str],
                                output_dir: Path, logger: logging.Logger = None) -> pd.DataFrame:
    """Analyze if monthly Top N keywords from source groups appear later in target group.
    
    Args:
        source_groups: List of source group names (e.g., ['news', 'reddit'])
        target_group: Target group name (e.g., 'meeting')
        top_n: Number of top keywords per month
        exclude_keywords: List of keywords to exclude
        output_dir: Base output directory (output/tables)
        logger: Logger instance (optional)
        
    Returns:
        DataFrame with columns: token, source_group, source_month, source_first_date, 
                                target_first_date, days_lag, appears_in_target
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Load keyword_by_date for source groups
    # Try overall folder first, then root folder (for backward compatibility)
    source_keywords = {}
    for group in source_groups:
        # Try overall folder first (current structure)
        csv_path = output_dir / group / 'overall' / 'keyword_by_date.csv'
        if not csv_path.exists():
            # Fallback to root folder (for backward compatibility)
            csv_path = output_dir / group / 'keyword_by_date.csv'
        
        df = load_keyword_by_date(csv_path)
        if len(df) > 0:
            source_keywords[group] = df
            logger.info(f"Loaded {len(df)} keyword-date records from {group}")
        else:
            logger.warning(f"No keyword_by_date.csv found for source group: {group} (tried: {csv_path})")
    
    # Load keyword_by_date for target group
    # Try overall folder first, then root folder (for backward compatibility)
    target_csv_path = output_dir / target_group / 'overall' / 'keyword_by_date.csv'
    if not target_csv_path.exists():
        # Fallback to root folder (for backward compatibility)
        target_csv_path = output_dir / target_group / 'keyword_by_date.csv'
    
    target_df = load_keyword_by_date(target_csv_path)
    if len(target_df) > 0:
        logger.info(f"Loaded {len(target_df)} keyword-date records from {target_group}")
    else:
        logger.warning(f"No keyword_by_date.csv found for target group: {target_group} (tried: {target_csv_path})")
    
    # Get monthly Top N keywords for each source group
    source_monthly_topn = {}
    for group in source_groups:
        if group in source_keywords:
            monthly_topn = get_monthly_topn_keywords(source_keywords[group], top_n, exclude_keywords)
            source_monthly_topn[group] = monthly_topn
            total_months = len(monthly_topn)
            total_keywords = sum(len(kw_list) for kw_list in monthly_topn.values())
            logger.info(f"{group}: {total_months} months, {total_keywords} monthly Top {top_n} keywords")
    
    # Create target keyword first dates mapping
    target_first_dates = {}
    if len(target_df) > 0:
        # Filter exclude keywords from target
        if exclude_keywords:
            exclude_set = {kw.lower() for kw in exclude_keywords}
            target_df_filtered = target_df[~target_df['token'].str.lower().isin(exclude_set)].copy()
        else:
            target_df_filtered = target_df.copy()
        
        target_first_dates = target_df_filtered.groupby('token')['date'].min().to_dict()
    
    # Analyze each keyword from monthly Top N
    results = []
    
    for group in source_groups:
        if group not in source_monthly_topn:
            continue
        
        for month, keywords in source_monthly_topn[group].items():
            # Get first date in this month for each keyword
            month_start = pd.to_datetime(f"{month}-01")
            month_end = month_start + pd.offsets.MonthEnd(0)
            
            month_data = source_keywords[group][
                (source_keywords[group]['date'] >= month_start) &
                (source_keywords[group]['date'] <= month_end)
            ]
            
            for token in keywords:
                # Get first date in this month
                token_month_data = month_data[month_data['token'] == token]
                if len(token_month_data) == 0:
                    continue
                
                source_first_date = token_month_data['date'].min()
                
                # Check if keyword appears in target group
                target_first_date = target_first_dates.get(token)
                
                if target_first_date is not None:
                    # Keyword appears in target
                    days_lag = (target_first_date - source_first_date).days
                    appears_in_target = True
                else:
                    # Keyword does not appear in target
                    days_lag = None
                    appears_in_target = False
                    target_first_date = None
                
                results.append({
                    'token': token,
                    'source_group': group,
                    'source_month': month,
                    'source_first_date': source_first_date,
                    'target_first_date': target_first_date,
                    'days_lag': days_lag,
                    'appears_in_target': appears_in_target
                })
    
    df = pd.DataFrame(results)
    
    # Sort by source_month and token
    if len(df) > 0:
        df = df.sort_values(['source_month', 'token'])
    
    return df

