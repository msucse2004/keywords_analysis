"""
Analyze keyword lag: Check if keywords from news/reddit appear later in meeting.
Uses monthly Top N keywords and excludes noise keywords.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import yaml


def load_exclude_keywords(exclude_dir: Path) -> List[str]:
    """Load exclude keywords from data/exclude folder.
    
    Reads all .txt files in the exclude directory and extracts
    comma-separated keywords from each file.
    
    Args:
        exclude_dir: Directory containing exclude keyword files
        
    Returns:
        List of exclude keywords (lowercased, deduplicated)
    """
    exclude_keywords = []
    
    if not exclude_dir.exists():
        return exclude_keywords
    
    # Read all .txt files in exclude directory
    for txt_file in exclude_dir.glob('*.txt'):
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    # Split by comma and clean up
                    keywords = [kw.strip().lower() for kw in content.split(',') if kw.strip()]
                    exclude_keywords.extend(keywords)
        except Exception as e:
            print(f"Warning: Error reading exclude file {txt_file}: {e}")
    
    # Remove duplicates and return
    return list(set(exclude_keywords))


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
                                output_dir: Path = Path('output/tables')) -> pd.DataFrame:
    """Analyze if monthly Top N keywords from source groups appear later in target group.
    
    Args:
        source_groups: List of source group names (e.g., ['news', 'reddit'])
        target_group: Target group name (e.g., 'meeting')
        top_n: Number of top keywords per month
        exclude_keywords: List of keywords to exclude
        output_dir: Base output directory
        
    Returns:
        DataFrame with columns: token, source_group, source_month, source_first_date, 
                                target_first_date, days_lag, appears_in_target
    """
    # Load keyword_by_date for source groups
    source_keywords = {}
    for group in source_groups:
        csv_path = output_dir / group / 'keyword_by_date.csv'
        df = load_keyword_by_date(csv_path)
        if len(df) > 0:
            source_keywords[group] = df
            print(f"Loaded {len(df)} keyword-date records from {group}")
    
    # Load keyword_by_date for target group
    target_csv_path = output_dir / target_group / 'keyword_by_date.csv'
    target_df = load_keyword_by_date(target_csv_path)
    if len(target_df) > 0:
        print(f"Loaded {len(target_df)} keyword-date records from {target_group}")
    
    # Get monthly Top N keywords for each source group
    source_monthly_topn = {}
    for group in source_groups:
        if group in source_keywords:
            monthly_topn = get_monthly_topn_keywords(source_keywords[group], top_n, exclude_keywords)
            source_monthly_topn[group] = monthly_topn
            total_months = len(monthly_topn)
            total_keywords = sum(len(kw_list) for kw_list in monthly_topn.values())
            print(f"{group}: {total_months} months, {total_keywords} monthly Top {top_n} keywords")
    
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


def main():
    """Main analysis function."""
    # Load configuration
    config_path = Path('config/default.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    top_n = config.get('KEYWORD_TOP_N', 50)
    print(f"Using KEYWORD_TOP_N: {top_n}")
    
    # Load exclude keywords
    exclude_dir = Path('data/exclude')
    exclude_keywords = load_exclude_keywords(exclude_dir)
    print(f"Loaded {len(exclude_keywords)} exclude keywords")
    
    output_dir = Path('output/tables')
    time_lagging_dir = Path('output/TimeLagging')
    time_lagging_dir.mkdir(parents=True, exist_ok=True)
    output_file = time_lagging_dir / 'keyword_lag_analysis.csv'
    
    print("=" * 80)
    print("Keyword Lag Analysis: News/Reddit (Monthly Top N) -> Meeting")
    print("=" * 80)
    
    # Analyze keywords from news and reddit appearing in meeting
    df = analyze_keyword_lag_monthly(
        source_groups=['news', 'reddit'],
        target_group='meeting',
        top_n=top_n,
        exclude_keywords=exclude_keywords,
        output_dir=output_dir
    )
    
    # Save results
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    
    total_keywords = len(df)
    appears_in_meeting = df['appears_in_target'].sum()
    percentage = (appears_in_meeting / total_keywords * 100) if total_keywords > 0 else 0
    
    print(f"Total monthly Top {top_n} keywords from news/reddit: {total_keywords}")
    print(f"Keywords that appear in meeting: {appears_in_meeting} ({percentage:.1f}%)")
    print(f"Keywords that do NOT appear in meeting: {total_keywords - appears_in_meeting}")
    
    # Analyze time lag for keywords that appear in meeting
    df_with_lag = df[df['appears_in_target']].copy()
    if len(df_with_lag) > 0:
        print(f"\nTime Lag Statistics (for keywords appearing in meeting):")
        print(f"  Average lag: {df_with_lag['days_lag'].mean():.1f} days")
        print(f"  Median lag: {df_with_lag['days_lag'].median():.1f} days")
        print(f"  Min lag: {df_with_lag['days_lag'].min():.0f} days")
        print(f"  Max lag: {df_with_lag['days_lag'].max():.0f} days")
        
        # Count by lag categories
        negative_lag = (df_with_lag['days_lag'] < 0).sum()
        zero_lag = (df_with_lag['days_lag'] == 0).sum()
        positive_lag = (df_with_lag['days_lag'] > 0).sum()
        
        print(f"\nLag Categories:")
        print(f"  Appears earlier in meeting: {negative_lag}")
        print(f"  Appears on same day: {zero_lag}")
        print(f"  Appears later in meeting: {positive_lag}")
    
    # Show top keywords by lag
    if len(df_with_lag) > 0:
        print("\n" + "=" * 80)
        print("Top 20 Keywords by Largest Lag (appearing later in meeting)")
        print("=" * 80)
        df_sorted = df_with_lag.nlargest(20, 'days_lag')[['token', 'source_group', 'source_month', 'source_first_date', 'target_first_date', 'days_lag']]
        print(df_sorted.to_string(index=False))
    
    # Run R script to generate visualizations
    print("\n" + "=" * 80)
    print("Generating visualizations...")
    print("=" * 80)
    
    import subprocess
    import os
    
    project_root = Path(__file__).parent
    r_script = project_root / 'r' / 'plot_keyword_lag.R'
    
    if r_script.exists():
        try:
            env = os.environ.copy()
            env['R_TABLES_DIR'] = str(time_lagging_dir)
            env['R_FIGURES_DIR'] = str(time_lagging_dir)
            env['R_PROJECT_ROOT'] = str(project_root)
            
            result = subprocess.run(
                ['conda', 'run', '-n', 'keyword-analysis', 'Rscript', str(r_script)],
                cwd=str(project_root),
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            print("Visualizations generated successfully!")
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to generate visualizations: {e}")
            if e.stderr:
                print(f"R error: {e.stderr}")
        except Exception as e:
            print(f"Warning: Error running R script: {e}")
    else:
        print(f"Warning: R script not found: {r_script}")


if __name__ == '__main__':
    main()
