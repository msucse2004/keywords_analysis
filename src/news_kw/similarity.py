"""Similarity analysis between groups."""

from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from sklearn.metrics.pairwise import cosine_similarity


def load_keyword_vectors(group_name: str, output_dir: Path, year: int = None) -> pd.Series:
    """Load keyword frequency vector for a group.
    
    Args:
        group_name: Name of the group
        output_dir: Base output directory
        year: Year (None for overall)
        
    Returns:
        Series with token as index and freq as values
    """
    if year is None:
        csv_path = output_dir / 'tables' / group_name / 'keyword_topk.csv'
    else:
        csv_path = output_dir / 'tables' / group_name / str(year) / 'keyword_topk.csv'
    
    if not csv_path.exists():
        return pd.Series(dtype=float)
    
    df = pd.read_csv(csv_path)
    return df.set_index('token')['freq']


def calculate_cosine_similarity(vec1: pd.Series, vec2: pd.Series) -> float:
    """Calculate cosine similarity between two keyword vectors.
    
    Args:
        vec1: First keyword vector (token -> freq)
        vec2: Second keyword vector (token -> freq)
        
    Returns:
        Cosine similarity (0-1)
    """
    # Get union of all keywords
    all_tokens = set(vec1.index) | set(vec2.index)
    
    if len(all_tokens) == 0:
        return 0.0
    
    # Create aligned vectors
    vec1_aligned = np.array([vec1.get(token, 0) for token in all_tokens])
    vec2_aligned = np.array([vec2.get(token, 0) for token in all_tokens])
    
    # Calculate cosine similarity
    if np.all(vec1_aligned == 0) or np.all(vec2_aligned == 0):
        return 0.0
    
    # Reshape for sklearn
    vec1_2d = vec1_aligned.reshape(1, -1)
    vec2_2d = vec2_aligned.reshape(1, -1)
    
    similarity = cosine_similarity(vec1_2d, vec2_2d)[0, 0]
    return float(similarity)


def calculate_jaccard_similarity(vec1: pd.Series, vec2: pd.Series) -> float:
    """Calculate Jaccard similarity between two keyword sets.
    
    Args:
        vec1: First keyword vector (token -> freq)
        vec2: Second keyword vector (token -> freq)
        
    Returns:
        Jaccard similarity (0-1)
    """
    set1 = set(vec1.index)
    set2 = set(vec2.index)
    
    if len(set1) == 0 and len(set2) == 0:
        return 1.0
    if len(set1) == 0 or len(set2) == 0:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def calculate_similarity_matrix(group_names: List[str], output_dir: Path, 
                                year: int = None, similarity_type: str = 'cosine') -> pd.DataFrame:
    """Calculate similarity matrix between groups.
    
    Args:
        group_names: List of group names
        output_dir: Base output directory
        year: Year (None for overall)
        similarity_type: 'cosine' or 'jaccard'
        
    Returns:
        DataFrame with similarity matrix (group_names x group_names)
    """
    # Load vectors for all groups
    vectors = {}
    for group in group_names:
        vec = load_keyword_vectors(group, output_dir, year)
        if len(vec) > 0:
            vectors[group] = vec
    
    if len(vectors) == 0:
        return pd.DataFrame()
    
    # Calculate similarity matrix
    similarity_func = calculate_cosine_similarity if similarity_type == 'cosine' else calculate_jaccard_similarity
    
    similarity_matrix = pd.DataFrame(index=group_names, columns=group_names)
    
    for group1 in group_names:
        for group2 in group_names:
            if group1 not in vectors or group2 not in vectors:
                similarity_matrix.loc[group1, group2] = np.nan
            elif group1 == group2:
                similarity_matrix.loc[group1, group2] = 1.0
            else:
                sim = similarity_func(vectors[group1], vectors[group2])
                similarity_matrix.loc[group1, group2] = sim
    
    return similarity_matrix.astype(float)


def get_available_years(group_names: List[str], output_dir: Path) -> List[int]:
    """Get list of years available across all groups.
    
    Args:
        group_names: List of group names
        output_dir: Base output directory
        
    Returns:
        Sorted list of years
    """
    years = set()
    
    for group in group_names:
        group_dir = output_dir / 'tables' / group
        if group_dir.exists():
            for item in group_dir.iterdir():
                if item.is_dir() and item.name.isdigit():
                    years.add(int(item.name))
    
    return sorted(years)


def create_similarity_analysis(output_dir: Path, group_names: List[str]):
    """Create similarity analysis for all groups.
    
    Creates:
    1. Overall similarity matrix (all groups)
    2. Year-by-year similarity matrices
    
    Args:
        output_dir: Base output directory
        group_names: List of group names to analyze
    """
    comparison_dir = output_dir / 'Comparison'
    comparison_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = comparison_dir / 'tables'
    tables_dir.mkdir(parents=True, exist_ok=True)
    
    # Overall similarity (cosine)
    overall_cosine = calculate_similarity_matrix(group_names, output_dir, year=None, similarity_type='cosine')
    if not overall_cosine.empty:
        overall_cosine.to_csv(tables_dir / 'similarity_overall_cosine.csv')
    
    # Overall similarity (jaccard)
    overall_jaccard = calculate_similarity_matrix(group_names, output_dir, year=None, similarity_type='jaccard')
    if not overall_jaccard.empty:
        overall_jaccard.to_csv(tables_dir / 'similarity_overall_jaccard.csv')
    
    # Year-by-year similarity
    years = get_available_years(group_names, output_dir)
    
    year_cosine_matrices = {}
    year_jaccard_matrices = {}
    
    for year in years:
        year_cosine = calculate_similarity_matrix(group_names, output_dir, year=year, similarity_type='cosine')
        if not year_cosine.empty:
            year_cosine_matrices[year] = year_cosine
            year_cosine.to_csv(tables_dir / f'similarity_{year}_cosine.csv')
        
        year_jaccard = calculate_similarity_matrix(group_names, output_dir, year=year, similarity_type='jaccard')
        if not year_jaccard.empty:
            year_jaccard_matrices[year] = year_jaccard
            year_jaccard.to_csv(tables_dir / f'similarity_{year}_jaccard.csv')
    
    return {
        'overall_cosine': overall_cosine,
        'overall_jaccard': overall_jaccard,
        'year_cosine': year_cosine_matrices,
        'year_jaccard': year_jaccard_matrices,
        'years': years
    }


def create_similarity_analysis_single_groups(output_dir: Path, group_names: List[str], tables_dir: Path):
    """Create similarity analysis for single groups only.
    
    Creates:
    1. Overall similarity matrix (single groups only)
    2. Year-by-year similarity matrices (single groups only)
    
    Args:
        output_dir: Base output directory
        group_names: List of single group names to analyze
        tables_dir: Directory to save tables
    """
    # Overall similarity (cosine)
    overall_cosine = calculate_similarity_matrix(group_names, output_dir, year=None, similarity_type='cosine')
    if not overall_cosine.empty:
        overall_cosine.to_csv(tables_dir / 'similarity_overall_cosine.csv')
    
    # Overall similarity (jaccard)
    overall_jaccard = calculate_similarity_matrix(group_names, output_dir, year=None, similarity_type='jaccard')
    if not overall_jaccard.empty:
        overall_jaccard.to_csv(tables_dir / 'similarity_overall_jaccard.csv')
    
    # Year-by-year similarity
    years = get_available_years(group_names, output_dir)
    
    for year in years:
        year_cosine = calculate_similarity_matrix(group_names, output_dir, year=year, similarity_type='cosine')
        if not year_cosine.empty:
            year_cosine.to_csv(tables_dir / f'similarity_{year}_cosine.csv')
        
        year_jaccard = calculate_similarity_matrix(group_names, output_dir, year=year, similarity_type='jaccard')
        if not year_jaccard.empty:
            year_jaccard.to_csv(tables_dir / f'similarity_{year}_jaccard.csv')

