"""Text preprocessing and tokenization."""

import re
import nltk
import os
import warnings
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from tqdm import tqdm

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except:
        pass

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    try:
        nltk.download('punkt_tab', quiet=True)
    except:
        pass

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


def preprocess_text(text: str) -> str:
    """Preprocess text: lowercase, remove URLs, clean special characters.
    
    Args:
        text: Raw text
        
    Returns:
        Preprocessed text
    """
    # Lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Keep only alphanumeric and spaces
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def _tokenize_single_document(row_tuple: tuple) -> list:
    """Tokenize a single document (for parallel processing).
    
    Args:
        row_tuple: Tuple of (doc_id, date, text)
        
    Returns:
        List of token dicts
    """
    doc_id, date, text = row_tuple
    
    # Download NLTK data if needed (each process needs its own)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
        except:
            pass
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    
    stop_words = set(stopwords.words('english'))
    
    # Preprocess
    preprocessed = preprocess_text(text)
    
    # Tokenize
    words = word_tokenize(preprocessed)
    
    # Filter: remove stopwords, keep only alphabetic tokens with length >= 2
    tokens = [
        word for word in words
        if word.isalpha() and len(word) >= 2 and word not in stop_words
    ]
    
    # Return list of token dicts
    return [
        {
            'doc_id': doc_id,
            'date': date,
            'token': token
        }
        for token in tokens
    ]


def tokenize_documents(df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Tokenize documents and create tokens table.
    
    Args:
        df: DataFrame with columns: doc_id, date, text
        output_dir: Directory to save tokens CSV
        
    Returns:
        DataFrame with columns: doc_id, date, token
    """
    num_docs = len(df)
    
    # Calculate number of workers (70% of CPU cores)
    cpu_count = os.cpu_count() or 1
    max_workers = max(1, int(cpu_count * 0.7))
    workers = min(max_workers, num_docs)
    
    tokens_list = []
    
    if num_docs > 50 and workers > 1:
        # Parallel processing for large document sets
        # Prepare data for parallel processing
        doc_tuples = [(row['doc_id'], row['date'], row['text']) for _, row in df.iterrows()]
        processed_docs = set()
        failed_docs = []
        
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_tokenize_single_document, doc_tuple): doc_tuple 
                      for doc_tuple in doc_tuples}
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="Tokenizing"):
                doc_tuple = futures[future]
                doc_id = doc_tuple[0]
                try:
                    result = future.result()
                    tokens_list.extend(result)
                    processed_docs.add(doc_id)
                except Exception as e:
                    failed_docs.append((doc_id, str(e)))
                    warnings.warn(f"Error tokenizing document {doc_id}: {e}")
                    continue
        
        # Verify all documents were processed
        total_processed = len(processed_docs) + len(failed_docs)
        if total_processed != num_docs:
            missing_count = num_docs - total_processed
            warnings.warn(
                f"문서 토큰화 누락 경고: {missing_count}개 문서가 처리되지 않았습니다. "
                f"(전체: {num_docs}, 처리됨: {len(processed_docs)}, 실패: {len(failed_docs)})"
            )
        
        # Log detailed statistics
        if failed_docs:
            warnings.warn(
                f"토큰화 요약: 성공 {len(processed_docs)}개, 실패 {len(failed_docs)}개"
            )
            if len(failed_docs) <= 10:
                warnings.warn(f"실패한 문서 목록:")
                for doc_id, error in failed_docs:
                    warnings.warn(f"  - {doc_id}: {error}")
            else:
                warnings.warn(f"실패한 문서 목록 (최대 10개):")
                for doc_id, error in failed_docs[:10]:
                    warnings.warn(f"  - {doc_id}: {error}")
                warnings.warn(f"  ... 외 {len(failed_docs) - 10}개 문서 실패")
    else:
        # Sequential processing for small document sets
        stop_words = set(stopwords.words('english'))
        
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Tokenizing"):
            doc_id = row['doc_id']
            date = row['date']
            text = row['text']
            
            # Preprocess
            preprocessed = preprocess_text(text)
            
            # Tokenize
            words = word_tokenize(preprocessed)
            
            # Filter: remove stopwords, keep only alphabetic tokens with length >= 2
            tokens = [
                word for word in words
                if word.isalpha() and len(word) >= 2 and word not in stop_words
            ]
            
            # Add to list
            for token in tokens:
                tokens_list.append({
                    'doc_id': doc_id,
                    'date': date,
                    'token': token
                })
    
    tokens_df = pd.DataFrame(tokens_list)
    
    # Save to CSV
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'tokens.csv'
    tokens_df.to_csv(output_path, index=False)
    
    return tokens_df

