"""Keyword co-occurrence network analysis."""

from pathlib import Path
import pandas as pd
from collections import defaultdict
from news_kw.config import Config


def calculate_cooccurrence(tokens_df: pd.DataFrame, config: Config, output_dir: Path, exclude_keywords: list = None):
    """Calculate keyword co-occurrence network.
    
    Args:
        tokens_df: DataFrame with columns: doc_id, date, token
        config: Configuration object
        output_dir: Directory to save output tables
        exclude_keywords: List of keywords to exclude (case-insensitive)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter out excluded keywords (case-insensitive)
    if exclude_keywords:
        exclude_set = {kw.lower() for kw in exclude_keywords}
        tokens_df = tokens_df[~tokens_df['token'].str.lower().isin(exclude_set)].copy()
    
    # Calculate document frequency for each token
    doc_freq = tokens_df.groupby('token')['doc_id'].nunique().reset_index()
    doc_freq.columns = ['token', 'doc_freq']
    doc_freq = doc_freq.sort_values('doc_freq', ascending=False)
    
    # Filter out excluded keywords from doc_freq as well (safety check)
    if exclude_keywords:
        exclude_set = {kw.lower() for kw in exclude_keywords}
        doc_freq = doc_freq[~doc_freq['token'].str.lower().isin(exclude_set)].copy()
    
    # Get top N nodes by document frequency
    top_nodes = set(doc_freq.head(config.COOC_NODE_TOP_N)['token'])
    
    # Filter tokens to top nodes only
    filtered_tokens = tokens_df[tokens_df['token'].isin(top_nodes)].copy()
    
    # Calculate co-occurrence (within same document)
    cooc_dict = defaultdict(int)
    
    for doc_id, group in filtered_tokens.groupby('doc_id'):
        tokens_in_doc = list(group['token'].unique())
        
        # Count pairs
        for i, token1 in enumerate(tokens_in_doc):
            for token2 in tokens_in_doc[i+1:]:
                # Ensure consistent ordering
                pair = tuple(sorted([token1, token2]))
                cooc_dict[pair] += 1
    
    # Convert to DataFrame
    edges = pd.DataFrame([
        {'source': pair[0], 'target': pair[1], 'weight': count}
        for pair, count in cooc_dict.items()
    ])
    
    # Get top N edges by weight
    edges = edges.sort_values('weight', ascending=False).head(config.COOC_EDGE_TOP_N)
    
    # Create nodes table (only tokens that appear in edges)
    nodes_in_edges = set(edges['source']) | set(edges['target'])
    nodes = doc_freq[doc_freq['token'].isin(nodes_in_edges)].copy()
    nodes = nodes.sort_values('doc_freq', ascending=False)
    
    # Save nodes
    nodes_path = output_dir / 'cooccurrence_nodes.csv'
    nodes.to_csv(nodes_path, index=False)
    
    # Save edges
    edges_path = output_dir / 'cooccurrence_edges.csv'
    edges.to_csv(edges_path, index=False)

