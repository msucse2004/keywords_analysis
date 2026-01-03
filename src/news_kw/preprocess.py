"""Text preprocessing and tokenization."""

import re
import nltk
from pathlib import Path
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


def tokenize_documents(df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Tokenize documents and create tokens table.
    
    Args:
        df: DataFrame with columns: doc_id, date, text
        output_dir: Directory to save tokens CSV
        
    Returns:
        DataFrame with columns: doc_id, date, token
    """
    stop_words = set(stopwords.words('english'))
    
    tokens_list = []
    
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

