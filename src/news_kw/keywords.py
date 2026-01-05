"""Keyword extraction and frequency analysis."""

from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from news_kw.config import Config


def extract_keywords(tokens_df: pd.DataFrame, config: Config, exclude_keywords: list, output_dir: Path) -> pd.DataFrame:
    """Extract top keywords by frequency and TF-IDF.
    
    Args:
        tokens_df: DataFrame with columns: doc_id, date, token
        config: Configuration object
        exclude_keywords: List of keywords to exclude
        output_dir: Directory to save output tables
        
    Returns:
        DataFrame with top keywords (token, freq)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter out excluded keywords (case-insensitive)
    if exclude_keywords:
        exclude_set = {kw.lower() for kw in exclude_keywords}
        tokens_df = tokens_df[~tokens_df['token'].str.lower().isin(exclude_set)].copy()
    
    # Overall frequency
    keyword_freq = tokens_df['token'].value_counts()
    
    # Filter out excluded keywords from frequency before selecting top N
    if exclude_keywords:
        exclude_set = {kw.lower() for kw in exclude_keywords}
        keyword_freq = keyword_freq[~keyword_freq.index.str.lower().isin(exclude_set)]
    
    keyword_topk = keyword_freq.head(config.KEYWORD_TOP_N).reset_index()
    keyword_topk.columns = ['token', 'freq']
    
    # Save keyword topk
    output_path = output_dir / 'keyword_topk.csv'
    keyword_topk.to_csv(output_path, index=False)
    
    # TF-IDF calculation (document level)
    # Group tokens by document
    doc_tokens = tokens_df.groupby('doc_id')['token'].apply(lambda x: ' '.join(x)).reset_index()
    
    # Calculate TF-IDF
    vectorizer = TfidfVectorizer(max_features=config.KEYWORD_TOP_N * 2, lowercase=True)
    tfidf_matrix = vectorizer.fit_transform(doc_tokens['token'])
    
    # Get feature names
    feature_names = vectorizer.get_feature_names_out()
    
    # Calculate mean TF-IDF across all documents
    mean_tfidf = tfidf_matrix.mean(axis=0).A1
    tfidf_scores = pd.DataFrame({
        'token': feature_names,
        'score': mean_tfidf
    }).sort_values('score', ascending=False).head(config.KEYWORD_TOP_N)
    
    # Save TF-IDF topk
    tfidf_path = output_dir / 'tfidf_topk.csv'
    tfidf_scores.to_csv(tfidf_path, index=False)
    
    # Keyword by date (aggregated by month)
    tokens_df['date'] = pd.to_datetime(tokens_df['date'])
    tokens_df['month'] = tokens_df['date'].dt.to_period('M')
    keyword_by_date = tokens_df.groupby(['month', 'token']).size().reset_index(name='freq')
    # Convert month period to string format (YYYY-MM)
    keyword_by_date['date'] = keyword_by_date['month'].astype(str)
    keyword_by_date = keyword_by_date.drop(columns=['month'])
    keyword_by_date = keyword_by_date.sort_values(['date', 'freq'], ascending=[True, False])
    
    # Save keyword by date
    keyword_date_path = output_dir / 'keyword_by_date.csv'
    keyword_by_date.to_csv(keyword_date_path, index=False)
    
    return keyword_topk

