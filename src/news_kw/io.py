"""Input/output operations for loading TXT and PDF news articles."""

import re
import warnings
from pathlib import Path
from typing import Optional
import pandas as pd
from tqdm import tqdm

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    warnings.warn("pdfplumber not available, PDF support disabled")


def parse_date_from_text(text: str) -> Optional[str]:
    """Extract date from text header (Date: YYYY-MM-DD format).
    
    Args:
        text: Full text content
        
    Returns:
        Date string in YYYY-MM-DD format or None
    """
    match = re.search(r'Date:\s*(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def parse_date_from_path(file_path: Path) -> Optional[str]:
    """Extract date from file path (YYYY-MM-DD or YYYY_MM_DD in filename).
    
    Args:
        file_path: Path to the file
        
    Returns:
        Date string in YYYY-MM-DD format or None
    """
    # Check filename for YYYY-MM-DD or YYYY_MM_DD
    filename_match = re.search(r'(\d{4})[-_](\d{2})[-_](\d{2})', file_path.name)
    if filename_match:
        year, month, day = filename_match.groups()
        return f"{year}-{month}-{day}"
    
    return None


def parse_title_from_text(text: str) -> Optional[str]:
    """Extract title from text header (Title: ... format).
    
    Args:
        text: Full text content
        
    Returns:
        Title string or None
    """
    match = re.search(r'Title:\s*(.+?)(?:\n|$)', text, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def parse_source_from_text(text: str) -> Optional[str]:
    """Extract source from text header (Source: ... format).
    
    Args:
        text: Full text content
        
    Returns:
        Source string or None
    """
    match = re.search(r'Source:\s*(.+?)(?:\n|$)', text, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def extract_text_from_pdf(pdf_path: Path) -> Optional[str]:
    """Extract text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extracted text or None if error
    """
    if not PDF_SUPPORT:
        return None
    
    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n'.join(text_parts)
    except Exception as e:
        warnings.warn(f"Error extracting text from PDF {pdf_path}: {e}")
        return None


def extract_body_text(text: str) -> str:
    """Extract body text by removing header lines.
    
    Args:
        text: Full text content
        
    Returns:
        Body text without headers
    """
    lines = text.split('\n')
    body_lines = []
    skip_headers = False
    
    for line in lines:
        # Skip header lines
        if re.match(r'^(Title|Date|Source):', line, re.IGNORECASE):
            skip_headers = True
            continue
        
        # After headers, start collecting body
        if skip_headers and line.strip():
            body_lines.append(line)
        elif not skip_headers:
            body_lines.append(line)
    
    return '\n'.join(body_lines).strip()


def load_txt_articles(input_dir: Path, output_dir: Path) -> pd.DataFrame:
    """Load all TXT and PDF articles from directory recursively.
    
    Args:
        input_dir: Directory containing TXT and PDF files
        output_dir: Directory to save processed documents
        
    Returns:
        DataFrame with columns: doc_id, date, title, text, source
    """
    # Get both TXT and PDF files
    txt_files = list(input_dir.rglob('*.txt'))
    pdf_files = list(input_dir.rglob('*.pdf')) if PDF_SUPPORT else []
    all_files = txt_files + pdf_files
    
    if not all_files:
        raise ValueError(f"No TXT or PDF files found in {input_dir}")
    
    documents = []
    
    for file_path in tqdm(all_files, desc="Loading files"):
        try:
            # Extract text based on file type
            if file_path.suffix.lower() == '.pdf':
                content = extract_text_from_pdf(file_path)
                if not content:
                    warnings.warn(f"Could not extract text from PDF {file_path}, skipping")
                    continue
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            # Parse date (priority: text > filename)
            date_from_text = parse_date_from_text(content)
            date_from_filename = parse_date_from_path(file_path)
            
            # Use text date if available, otherwise filename date
            if date_from_text and date_from_filename:
                if date_from_text != date_from_filename:
                    warnings.warn(f"Date mismatch for {file_path}: text={date_from_text}, filename={date_from_filename}. Using text date.")
                date = date_from_text
            elif date_from_text:
                date = date_from_text
            elif date_from_filename:
                date = date_from_filename
            else:
                warnings.warn(f"Could not parse date for {file_path}, skipping")
                continue
            
            # Parse title
            title = parse_title_from_text(content)
            if not title:
                title = file_path.stem
            
            # Parse source
            source = parse_source_from_text(content)
            if not source:
                source = "unknown"
            
            # Extract body
            text = extract_body_text(content)
            
            if not text.strip():
                warnings.warn(f"Empty text for {file_path}, skipping")
                continue
            
            doc_id = f"{file_path.stem}_{file_path.parent.name}"
            
            documents.append({
                'doc_id': doc_id,
                'date': date,
                'title': title,
                'text': text,
                'source': source
            })
            
        except Exception as e:
            warnings.warn(f"Error processing {file_path}: {e}")
            continue
    
    if not documents:
        raise ValueError("No valid documents loaded")
    
    df = pd.DataFrame(documents)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # Save to parquet
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'documents.parquet'
    df.to_parquet(output_path, index=False)
    
    return df

