"""Filter files by date parsing and copy to filtered_data directory as TXT."""

import os
import sys
import re
import shutil
import yaml
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
import warnings
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from news_kw.io import parse_date_from_path, parse_date_from_text, extract_text_from_html, extract_text_from_pdf, extract_text_from_docx_with_fallback


def check_conda_environment():
    """Check if running in conda environment and warn if not."""
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    conda_prefix = os.environ.get('CONDA_PREFIX')
    
    # Check if we're in the expected conda environment
    expected_env = 'keyword-analysis'
    
    if not conda_env and not conda_prefix:
        warnings.warn(
            f"Warning: Not running in conda environment. "
            f"Expected environment: '{expected_env}'. "
            f"Please use 'conda run -n {expected_env} python -m news_kw.filter_files' "
            f"or use the provided run scripts (run_filter_files.bat or run_filter_files.ps1).",
            UserWarning
        )
    elif conda_env != expected_env:
        warnings.warn(
            f"Warning: Running in conda environment '{conda_env}' but expected '{expected_env}'. "
            f"Please use 'conda run -n {expected_env} python -m news_kw.filter_files' "
            f"or use the provided run scripts (run_filter_files.bat or run_filter_files.ps1).",
            UserWarning
        )

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    REPORTLAB_SUPPORT = True
except ImportError:
    REPORTLAB_SUPPORT = False
    warnings.warn("reportlab not available, text-to-PDF conversion will be limited")


def validate_date_parsing(file_path: Path) -> Optional[str]:
    """Validate that a file can have its date parsed from filename only.
    
    This function only checks the filename, not the file content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Parsed date string in YYYY-MM-DD format, or None if parsing failed
    """
    # Only parse from filename (no content reading)
    date_from_filename = parse_date_from_path(file_path)
    
    return date_from_filename


def convert_text_to_pdf(text: str, output_pdf_path: Path, title: str = "Document") -> bool:
    """Convert text content to PDF file.
    
    Args:
        text: Text content to convert
        output_pdf_path: Path to save PDF file
        title: Document title
        
    Returns:
        True if conversion successful, False otherwise
    """
    if not REPORTLAB_SUPPORT:
        warnings.warn("reportlab not available, cannot convert text to PDF")
        return False
    
    try:
        # Use SimpleDocTemplate for better text handling
        doc = SimpleDocTemplate(str(output_pdf_path), pagesize=A4,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=72)
        
        # Container for the 'Flowable' objects
        story = []
        styles = getSampleStyleSheet()
        
        # Split text into paragraphs and add to story
        paragraphs = text.split('\n')
        for para in paragraphs:
            if para.strip():
                # Replace special characters that might cause issues
                para_clean = para.replace('\x00', '')  # Remove null bytes
                try:
                    story.append(Paragraph(para_clean[:5000], styles['Normal']))  # Limit paragraph length
                    story.append(Spacer(1, 12))
                except Exception:
                    # If paragraph fails, try with escaped text
                    try:
                        import html
                        para_escaped = html.escape(para_clean[:5000])
                        story.append(Paragraph(para_escaped, styles['Normal']))
                        story.append(Spacer(1, 12))
                    except Exception:
                        continue
        
        if not story:
            return False
        
        # Build PDF
        try:
            doc.build(story)
            return True
        except Exception as e:
            warnings.warn(f"Error building PDF {output_pdf_path}: {e}")
            return False
    except Exception as e:
        warnings.warn(f"Error converting text to PDF {output_pdf_path}: {e}")
        return False


def convert_html_to_pdf(html_path: Path, output_pdf_path: Path) -> bool:
    """Convert HTML file to PDF.
    
    Args:
        html_path: Path to HTML file
        output_pdf_path: Path to save PDF file
        
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # Extract text from HTML
        text = extract_text_from_html(html_path)
        if not text:
            return False
        
        # Convert text to PDF
        return convert_text_to_pdf(text, output_pdf_path, title=html_path.stem)
    except Exception as e:
        warnings.warn(f"Error converting HTML to PDF {html_path}: {e}")
        return False


def convert_txt_to_pdf(txt_path: Path, output_pdf_path: Path) -> bool:
    """Convert TXT file to PDF.
    
    Args:
        txt_path: Path to TXT file
        output_pdf_path: Path to save PDF file
        
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # Read text from file
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        
        if not text.strip():
            return False
        
        # Convert text to PDF
        return convert_text_to_pdf(text, output_pdf_path, title=txt_path.stem)
    except Exception as e:
        warnings.warn(f"Error converting TXT to PDF {txt_path}: {e}")
        return False


def sanitize_filename(filename: str, max_length: int = 20) -> str:
    """Sanitize filename by removing special characters and limiting length.
    
    Args:
        filename: Original filename (without extension)
        max_length: Maximum length for filename (default: 20)
        
    Returns:
        Sanitized filename
    """
    # Remove special characters (keep only alphanumeric, spaces, hyphens, underscores)
    # Replace special characters with underscore
    sanitized = re.sub(r'[^\w\s-]', '_', filename)
    # Replace multiple spaces/underscores with single underscore
    sanitized = re.sub(r'[\s_]+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    # Remove trailing underscores after truncation
    sanitized = sanitized.rstrip('_')
    return sanitized


def find_original_file_from_filtered(filtered_file_path: Path, filtered_data_dir: Path, raw_txt_dir: Path) -> Optional[Path]:
    """Find the original file in raw_txt_dir that corresponds to a filtered_data file.
    
    This function reverses the sanitization process to find the original file.
    
    Args:
        filtered_file_path: Path to file in filtered_data (e.g., YYYY-MM-DD_sanitized_name.txt)
        filtered_data_dir: Root directory for filtered files
        raw_txt_dir: Root directory for raw files
        
    Returns:
        Original file path in raw_txt_dir, or None if not found
    """
    try:
        # Extract date prefix and sanitized stem from filtered filename
        # Format: YYYY-MM-DD_sanitized_stem.txt
        filename = filtered_file_path.name
        date_prefix_match = re.match(r'^(\d{4}-\d{2}-\d{2})_(.+?)\.txt$', filename)
        if not date_prefix_match:
            return None
        
        parsed_date, sanitized_stem = date_prefix_match.groups()
        
        # Get relative path from filtered_data_dir
        # filtered_file_path is like: data/filtered_data/reddit/2021/YYYY-MM-DD_name.txt
        # We need: reddit/2021/
        try:
            filtered_rel_path = filtered_file_path.relative_to(filtered_data_dir)
            folder_path = filtered_rel_path.parent  # Get folder part (reddit/2021)
        except ValueError:
            # If relative path calculation fails, try to extract from path
            path_parts = filtered_file_path.parts
            if 'filtered_data' in path_parts:
                idx = path_parts.index('filtered_data')
                folder_path = Path(*path_parts[idx+1:-1])  # Everything between filtered_data and filename
            else:
                return None
        
        # Look for original files in the corresponding raw_txt directory
        raw_folder = raw_txt_dir / folder_path
        if not raw_folder.exists():
            return None
        
        # Find files in raw_txt that could match
        # We need to check if sanitizing the original filename would match sanitized_stem
        # Use glob() instead of iterdir() to handle very long filenames on Windows
        from news_kw.io import parse_date_from_path
        
        candidates_by_date = []  # Store files with matching date as fallback
        # Try multiple file patterns to catch all files (PDF, DOCX, TXT, etc.)
        raw_files = list(raw_folder.glob('*.pdf')) + list(raw_folder.glob('*.docx')) + list(raw_folder.glob('*.txt')) + list(raw_folder.glob('*.html')) + list(raw_folder.glob('*.htm'))
        for raw_file in raw_files:
            if raw_file.is_file():
                # First, verify the date matches (this is the most important check)
                parsed_date_from_file = parse_date_from_path(raw_file)
                if parsed_date_from_file != parsed_date:
                    continue
                
                # Date matches, store as candidate
                candidates_by_date.append(raw_file)
                
                # Try filename matching
                original_stem = raw_file.stem
                # Sanitize original stem and compare
                sanitized_original = sanitize_filename(original_stem, max_length=1000)
                
                # Check if sanitized versions match (allowing for truncation)
                # Since sanitized_stem might be truncated, check if it's a prefix or matches
                # Also check reverse: sanitized_stem might be longer if original was truncated
                if (sanitized_stem == sanitized_original or 
                    sanitized_original.startswith(sanitized_stem) or 
                    sanitized_stem.startswith(sanitized_original)):
                    # Filename and date both match - this is the best match
                    return raw_file
        
        # If filename matching failed but we have candidates with matching dates,
        # use the best candidate (prefer files that have at least some common prefix)
        if candidates_by_date:
            # If there's only one candidate with matching date, use it
            if len(candidates_by_date) == 1:
                return candidates_by_date[0]
            
            # If multiple candidates, try to find the best match by checking prefix
            # (even if truncated, the prefix should match)
            sanitized_stem_lower = sanitized_stem.lower()
            for candidate in candidates_by_date:
                candidate_stem = candidate.stem
                sanitized_candidate = sanitize_filename(candidate_stem, max_length=1000).lower()
                # Check if the first part of sanitized_stem matches the beginning of sanitized_candidate
                if sanitized_stem_lower and sanitized_candidate.startswith(sanitized_stem_lower[:min(20, len(sanitized_stem_lower))]):
                    return candidate
            
            # If no prefix match, return the first candidate (better than nothing)
            return candidates_by_date[0]
        
        return None
    except Exception:
        return None


def create_destination_filename(source_path: Path, parsed_date: str, raw_txt_dir: Path, 
                                filtered_data_dir: Path) -> Path:
    """Create destination filename with date prefix and sanitized name.
    
    Args:
        source_path: Source file path
        parsed_date: Parsed date in YYYY-MM-DD format
        raw_txt_dir: Root directory for raw files
        filtered_data_dir: Root directory for filtered files
        
    Returns:
        Destination path with date prefix
    """
    # Get relative path from raw_txt_dir
    rel_path = source_path.relative_to(raw_txt_dir)
    
    # Get original filename without extension
    original_stem = source_path.stem
    
    # Sanitize filename (remove special chars)
    sanitized_stem = sanitize_filename(original_stem, max_length=1000)  # Don't truncate yet
    
    # Create new filename with date prefix: YYYY-MM-DD_sanitized_name.txt
    new_filename = f"{parsed_date}_{sanitized_stem}.txt"
    
    # Create destination path maintaining folder structure
    # Use the same folder structure but with new filename
    dest_path = filtered_data_dir / rel_path.parent / new_filename
    
    # Check if total path length is too long (Windows 260 char limit, but we'll use 200 as threshold)
    dest_path_str = str(dest_path)
    if len(dest_path_str) > 200:
        # Truncate filename to 50 characters (keeping extension)
        # Format: YYYY-MM-DD_ (11 chars) + filename (50 chars) + .txt (4 chars) = 65 chars max for filename part
        # But we need to account for folder path, so use 50 chars for the stem part
        max_stem_length = 50
        if len(sanitized_stem) > max_stem_length:
            sanitized_stem = sanitized_stem[:max_stem_length]
        
        # Recreate filename with truncated stem
        new_filename = f"{parsed_date}_{sanitized_stem}.txt"
        dest_path = filtered_data_dir / rel_path.parent / new_filename
        
        # If still too long, truncate more aggressively
        dest_path_str = str(dest_path)
        if len(dest_path_str) > 200:
            # Calculate available length for filename
            base_path_len = len(str(filtered_data_dir / rel_path.parent)) + 1  # +1 for separator
            available_for_filename = 200 - base_path_len - 1  # -1 for safety margin
            if available_for_filename > 15:  # At least YYYY-MM-DD_ (11) + some chars + .txt (4)
                max_stem_length = available_for_filename - 15  # 11 (date) + 4 (ext) = 15
                if max_stem_length > 0:
                    sanitized_stem = sanitized_stem[:max_stem_length]
                    new_filename = f"{parsed_date}_{sanitized_stem}.txt"
                    dest_path = filtered_data_dir / rel_path.parent / new_filename
    
    return dest_path


def convert_file_to_txt(source_path: Path, dest_txt_path: Path) -> bool:
    """Extract text from any file and save as TXT format.
    
    Args:
        source_path: Path to source file (PDF, DOCX, HTML, TXT)
        dest_txt_path: Path to save TXT file
        
    Returns:
        True if conversion successful, False otherwise
    """
    # Check if source file exists
    # For long paths on Windows, try with \\?\ prefix
    file_exists = False
    if source_path.exists():
        file_exists = True
    elif sys.platform == 'win32':
        # Try with long path prefix for Windows
        try:
            abs_path = source_path.resolve()
            long_path = '\\\\?\\' + str(abs_path)
            file_exists = os.path.exists(long_path)
        except Exception:
            file_exists = False
    
    if not file_exists:
        warnings.warn(f"Source file does not exist: {source_path}")
        return False
    
    file_ext = source_path.suffix.lower()
    
    # Extract text based on file type
    text = None
    
    # If already TXT, just copy
    if file_ext == '.txt':
        try:
            # Check path length (Windows 260 character limit)
            # Use long path prefix for both source and destination if needed
            dest_path_str = str(dest_txt_path)
            source_path_str = str(source_path)
            use_long_path = (len(dest_path_str) > 200 or len(source_path_str) > 200) and sys.platform == 'win32'
            
            if use_long_path:
                # Use \\?\ prefix for long paths (Windows)
                try:
                    abs_dest = dest_txt_path.resolve()
                    abs_source = source_path.resolve()
                    long_dest = '\\\\?\\' + str(abs_dest)
                    long_source = '\\\\?\\' + str(abs_source)
                    
                    # Create destination directory using long path
                    # Extract directory from long_dest string
                    dest_dir = os.path.dirname(long_dest)
                    try:
                        os.makedirs(dest_dir, exist_ok=True)
                    except Exception as dir_error:
                        warnings.warn(f"Cannot create directory for TXT {source_path.name}: {dir_error}")
                        return False
                    
                    # Copy using long paths
                    shutil.copy2(long_source, long_dest)
                    return True
                except Exception as long_path_error:
                    warnings.warn(f"Long path copy failed for {source_path.name}: {long_path_error}")
                    return False
            else:
                # Normal path handling
                try:
                    dest_txt_path.parent.mkdir(parents=True, exist_ok=True)
                except OSError as dir_error:
                    # If directory creation fails, try creating one level at a time
                    try:
                        parent = dest_txt_path.parent
                        parent.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        error_msg = f"Cannot create directory for TXT {source_path.name}: {dir_error}"
                        warnings.warn(error_msg)
                        return False
                
                shutil.copy2(source_path, dest_txt_path)
                return True
        except OSError as e:
            # Handle path length or permission issues
            error_msg = f"OS error copying TXT {source_path.name}: {e}"
            if hasattr(e, 'winerror'):
                error_msg += f" (WinError: {e.winerror})"
            warnings.warn(error_msg)
            return False
        except Exception as e:
            warnings.warn(f"Error copying TXT {source_path.name}: {type(e).__name__}: {e}")
            return False
    
    # Extract text from PDF
    elif file_ext == '.pdf':
        if not PDF_SUPPORT:
            warnings.warn(f"PDF support not available, cannot extract text from {source_path.name}")
            return False
        text = extract_text_from_pdf(source_path)
        if not text:
            return False
    
    # Extract text from DOCX
    elif file_ext == '.docx':
        if not DOCX_SUPPORT:
            warnings.warn(f"DOCX support not available, cannot extract text from {source_path.name}")
            return False
        text = extract_text_from_docx_with_fallback(source_path)
        if not text:
            return False
    
    # Extract text from HTML
    elif file_ext in ['.html', '.htm']:
        text = extract_text_from_html(source_path)
        if not text:
            return False
    
    else:
        warnings.warn(f"Unsupported file type for text extraction: {file_ext}")
        return False
    
    # Save extracted text to TXT file
    if text:
        try:
            dest_txt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_txt_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(text)
            return True
        except Exception as e:
            warnings.warn(f"Error saving text to TXT {source_path.name}: {type(e).__name__}: {e}")
            return False
    
    return False


def _process_single_file_for_filter(args: Tuple[Path, Path, Path]) -> Tuple[Optional[str], Optional[str]]:
    """Process a single file for filtering and conversion.
    
    This function is designed to be used with ProcessPoolExecutor.
    It processes one file: validates date parsing and converts to TXT.
    
    Args:
        args: Tuple of (file_path, raw_txt_dir, filtered_data_dir)
        
    Returns:
        Tuple of (success_file_path, error_message)
        - If successful: (file_path_str, None)
        - If failed: (None, error_message)
    """
    file_path, raw_txt_dir, filtered_data_dir = args
    
    try:
        # Validate date parsing
        parsed_date = validate_date_parsing(file_path)
        
        if parsed_date is None:
            return (None, str(file_path))
        
        # Create destination filename with date prefix and sanitized name
        dest_path = create_destination_filename(file_path, parsed_date, raw_txt_dir, filtered_data_dir)
        
        # Create parent directories (mkdir with exist_ok=True is thread-safe)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert file to TXT (or copy if already TXT)
        if not convert_file_to_txt(file_path, dest_path):
            # Try to get more specific error information
            if not file_path.exists():
                return (None, f"{str(file_path)} (File not found)")
            return (None, f"{str(file_path)} (TXT conversion failed)")
        
        return (str(file_path), None)
        
    except Exception as e:
        return (None, f"{str(file_path)} (Error: {str(e)})")


def filter_and_copy_files(raw_txt_dir: Path, filtered_data_dir: Path, 
                         config_path: Path) -> Dict[str, List[str]]:
    """Filter files by date parsing and copy to filtered_data directory.
    
    Args:
        raw_txt_dir: Directory containing raw files
        filtered_data_dir: Directory to copy filtered files to
        config_path: Path to config YAML file
        
    Returns:
        Dictionary with 'success' and 'failed' file lists
    """
    # Load config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    data_source_groups = config.get('DATA_SOURCE_GROUPS', [])
    
    # Get exclude folders, files, and path patterns from config
    exclude_folders = config.get('EXCLUDE_FOLDERS', ['_files'])
    exclude_files = config.get('EXCLUDE_FILES', ['fig_', '~$'])
    exclude_path_patterns = config.get('EXCLUDE_PATH_PATTERNS', [])
    
    # Collect all unique folder names from groups
    all_folders: Set[str] = set()
    for group in data_source_groups:
        if isinstance(group, list):
            all_folders.update(group)
        else:
            all_folders.add(group)
    
    # Find all files in raw_txt_dir
    txt_files = list(raw_txt_dir.rglob('*.txt'))
    pdf_files = list(raw_txt_dir.rglob('*.pdf')) if PDF_SUPPORT else []
    html_files = list(raw_txt_dir.rglob('*.html')) + list(raw_txt_dir.rglob('*.htm'))
    docx_files = list(raw_txt_dir.rglob('*.docx')) + list(raw_txt_dir.rglob('*.DOCX'))
    
    all_files = txt_files + pdf_files + html_files + docx_files
    
    # Filter files by source folders and exclude unwanted files
    filtered_files = []
    for file_path in all_files:
        try:
            rel_path = file_path.relative_to(raw_txt_dir)
            first_folder = rel_path.parts[0] if rel_path.parts else None
            
            # Skip if not in source folders
            if first_folder not in all_folders:
                continue
            
            # Check exclude folders from config (check if folder name appears in path parts or folder names contain it)
            should_exclude = False
            for folder_name in exclude_folders:
                # Check if folder name is exactly in path parts
                if folder_name in rel_path.parts:
                    should_exclude = True
                    break
                # Check if any folder name contains the exclude pattern
                for part in rel_path.parts:
                    if folder_name in part:
                        should_exclude = True
                        break
                if should_exclude:
                    break
            
            # Check exclude path patterns from config (check if pattern appears in relative path string)
            if not should_exclude:
                rel_path_str = str(rel_path)
                for pattern in exclude_path_patterns:
                    if pattern in rel_path_str:
                        should_exclude = True
                        break
            
            # Check exclude files from config (check if file name starts with excluded prefix)
            if not should_exclude:
                file_name = file_path.name
                for file_prefix in exclude_files:
                    if file_name.startswith(file_prefix):
                        should_exclude = True
                        break
            
            if should_exclude:
                continue
            
            filtered_files.append(file_path)
        except ValueError:
            continue
    
    # Validate dates and copy files
    successful_files = []
    failed_files = []
    failed_date_parsing = []  # Files that failed date parsing (filename only)
    
    num_files = len(filtered_files)
    print(f"Processing {num_files} files...")
    
    # Determine if we should use parallel processing
    cpu_count = os.cpu_count() or 1
    max_workers = max(1, int(cpu_count * 0.7))
    workers = min(max_workers, num_files)
    
    if num_files > 10 and workers > 1:
        # Parallel processing for large file sets
        print(f"Using parallel processing with {workers} workers...")
        
        # Prepare arguments for each file
        file_args = [(file_path, raw_txt_dir, filtered_data_dir) for file_path in filtered_files]
        
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_process_single_file_for_filter, args): args[0] 
                      for args in file_args}
            
            # Process all futures and track results
            for future in tqdm(as_completed(futures), total=len(futures), 
                              desc="Filtering and converting to TXT"):
                file_path = futures[future]
                try:
                    success_path, error_msg = future.result()
                    if success_path:
                        successful_files.append(success_path)
                    else:
                        failed_files.append(error_msg)
                        # Check if it's a date parsing failure (no "PDF conversion failed", "Error:", or "File not found" in message)
                        if error_msg and "TXT conversion failed" not in error_msg and "Error:" not in error_msg and "File not found" not in error_msg:
                            failed_date_parsing.append(error_msg)
                except Exception as e:
                    warnings.warn(f"Failed to process file {file_path}: {e}")
                    failed_files.append(str(file_path))
        
        # Verify all files were processed
        total_processed = len(successful_files) + len(failed_files)
        if total_processed != num_files:
            missing_count = num_files - total_processed
            warnings.warn(
                f"파일 처리 누락 경고: {missing_count}개 파일이 처리되지 않았습니다. "
                f"(전체: {num_files}, 성공: {len(successful_files)}, 실패: {len(failed_files)})"
            )
    else:
        # Sequential processing for small file sets
        for file_path in tqdm(filtered_files, desc="Filtering and converting to TXT"):
            try:
                # Validate date parsing (filename only, no content reading)
                parsed_date = validate_date_parsing(file_path)
                
                if parsed_date is None:
                    # File has no date in filename, add to failed list
                    failed_files.append(str(file_path))
                    failed_date_parsing.append(str(file_path))
                    continue
                
                # Create destination filename with date prefix and sanitized name
                dest_path = create_destination_filename(file_path, parsed_date, raw_txt_dir, filtered_data_dir)
                
                # Create parent directories
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert file to TXT (or copy if already TXT)
                if not convert_file_to_txt(file_path, dest_path):
                    failed_files.append(f"{str(file_path)} (TXT conversion failed)")
                    continue
                
                successful_files.append(str(file_path))
                
            except Exception as e:
                warnings.warn(f"Error processing {file_path}: {e}")
                failed_files.append(str(file_path))
    
    # Prepare failed_date_parsing.txt file path (will be written after finding missing files)
    failed_list_path = filtered_data_dir.parent / 'failed_date_parsing.txt'
    
    # Compare raw_txt and filtered_data to find missing files
    print("\n" + "=" * 80)
    print("Comparing raw_txt and filtered_data files...")
    print("=" * 80)
    
    # Get all files from raw_txt (after applying exclude rules)
    raw_txt_files_after_exclude = set()
    for file_path in all_files:
        try:
            rel_path = file_path.relative_to(raw_txt_dir)
            first_folder = rel_path.parts[0] if rel_path.parts else None
            
            # Skip if not in source folders
            if first_folder not in all_folders:
                continue
            
            # Check exclude rules (same logic as above)
            should_exclude = False
            for folder_name in exclude_folders:
                if folder_name in rel_path.parts:
                    should_exclude = True
                    break
                for part in rel_path.parts:
                    if folder_name in part:
                        should_exclude = True
                        break
                if should_exclude:
                    break
            
            if not should_exclude:
                rel_path_str = str(rel_path)
                for pattern in exclude_path_patterns:
                    if pattern in rel_path_str:
                        should_exclude = True
                        break
            
            if not should_exclude:
                file_name = file_path.name
                for file_prefix in exclude_files:
                    if file_name.startswith(file_prefix):
                        should_exclude = True
                        break
            
            if not should_exclude:
                raw_txt_files_after_exclude.add(str(rel_path))
        except ValueError:
            continue
    
    # Get successfully processed files (relative paths as strings)
    # Also check filtered_data directory to find files that were successfully processed
    successful_relative_paths = set()
    
    # First, add files from successful_files list
    for success_file in successful_files:
        try:
            success_path = Path(success_file)
            if success_path.exists():
                rel_path = success_path.relative_to(raw_txt_dir)
                successful_relative_paths.add(str(rel_path))
        except Exception:
            pass
    
    # Second, scan filtered_data directory to find all processed files
    # This catches files that were processed but might not be in successful_files list
    if filtered_data_dir.exists():
        for filtered_file in filtered_data_dir.rglob('*.txt'):
            # Check if filename has date prefix format (YYYY-MM-DD_)
            if re.match(r'^\d{4}-\d{2}-\d{2}_', filtered_file.name):
                # Find original file
                original_file = find_original_file_from_filtered(filtered_file, filtered_data_dir, raw_txt_dir)
                if original_file and original_file.exists():
                    try:
                        rel_path = original_file.relative_to(raw_txt_dir)
                        successful_relative_paths.add(str(rel_path))
                    except Exception:
                        pass
    
    # Get failed date parsing files (relative paths as strings)
    failed_date_relative_paths = set()
    for failed_file in failed_date_parsing:
        try:
            failed_path = Path(failed_file)
            if failed_path.exists():
                rel_path = failed_path.relative_to(raw_txt_dir)
                failed_date_relative_paths.add(str(rel_path))
        except Exception:
            # If it's already a relative path string, use it as is
            failed_date_relative_paths.add(failed_file)
    
    # Find missing files (in raw_txt but not in successful or failed_date_parsing)
    truly_missing = []
    for raw_rel_path_str in raw_txt_files_after_exclude:
        if raw_rel_path_str not in successful_relative_paths and raw_rel_path_str not in failed_date_relative_paths:
            truly_missing.append(raw_rel_path_str)
    
    # Add missing files to failed_date_parsing list and update the file
    if truly_missing:
        # Convert relative paths to full paths for failed_date_parsing
        missing_full_paths = []
        for missing_rel_path_str in truly_missing:
            missing_full_path = raw_txt_dir / missing_rel_path_str
            if missing_full_path.exists():
                missing_full_paths.append(str(missing_full_path))
            else:
                missing_full_paths.append(str(missing_rel_path_str))
        
        # Add missing files to failed_date_parsing list
        failed_date_parsing.extend(missing_full_paths)
        
        print(f"\n[WARNING] Found {len(truly_missing)} files missing from filtered_data")
        print(f"   Missing files will be added to: {failed_list_path}")
    else:
        print(f"\n[OK] All files accounted for")
        print(f"   Raw files (after exclude): {len(raw_txt_files_after_exclude)}")
        print(f"   Successfully processed: {len(successful_relative_paths)}")
        print(f"   Failed date parsing: {len(failed_date_relative_paths)}")
        print(f"   Total: {len(successful_relative_paths) + len(failed_date_relative_paths)}")
    
    # Write all failed files (date parsing failures + missing files) to failed_date_parsing.txt
    with open(failed_list_path, 'w', encoding='utf-8') as f:
        f.write("# Files that failed date parsing from filename or are missing from filtered_data\n")
        f.write("# Expected format: YYYY-MM-DD_filename.txt\n")
        f.write("# These files have no date information in their filename or were not processed\n")
        f.write("# Date parsing is done from filename only (no content reading)\n\n")
        f.write("# Excluded files (not included in this list):\n")
        for folder_name in exclude_folders:
            f.write(f"# - Folders named or containing: {folder_name}\n")
        for file_prefix in exclude_files:
            f.write(f"# - Files starting with: {file_prefix}\n")
        for pattern in exclude_path_patterns:
            f.write(f"# - Paths containing: {pattern}\n")
        f.write("\n")
        
        # Write all failed files (date parsing failures + missing files)
        all_failed_files = set()  # Use set to avoid duplicates
        for file_path in failed_date_parsing:
            # Skip excluded folders/files/paths in failed list
            should_skip = False
            file_path_str = str(file_path)
            # Check excluded folders
            for folder_name in exclude_folders:
                if folder_name in file_path_str:
                    should_skip = True
                    break
            # Check excluded path patterns
            if not should_skip:
                for pattern in exclude_path_patterns:
                    if pattern in file_path_str:
                        should_skip = True
                        break
            # Check excluded files
            if not should_skip:
                file_name = Path(file_path_str).name
                for file_prefix in exclude_files:
                    if file_name.startswith(file_prefix):
                        should_skip = True
                        break
            if not should_skip:
                all_failed_files.add(file_path_str)
        
        # Write all failed files (sorted)
        for file_path in sorted(all_failed_files):
            f.write(f"{file_path}\n")
    
    print(f"\nSummary:")
    print(f"  Successful: {len(successful_files)} files")
    print(f"  Failed: {len(failed_files)} files")
    print(f"  Failed files list saved to: {failed_list_path}")
    
    return {
        'success': successful_files,
        'failed': failed_files
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Filter files by date parsing and copy to filtered_data directory'
    )
    
    parser.add_argument(
        '--raw_dir',
        type=Path,
        default=Path('data/raw_txt'),
        help='Directory containing raw files (default: data/raw_txt)'
    )
    
    parser.add_argument(
        '--filtered_dir',
        type=Path,
        default=Path('data/filtered_data'),
        help='Directory to copy filtered files to (default: data/filtered_data)'
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config/default.yaml'),
        help='Path to config YAML file (default: config/default.yaml)'
    )
    
    args = parser.parse_args()
    
    # Check conda environment
    check_conda_environment()
    
    if not args.raw_dir.exists():
        raise FileNotFoundError(f"Raw directory not found: {args.raw_dir}")
    
    if not args.config.exists():
        raise FileNotFoundError(f"Config file not found: {args.config}")
    
    # Create filtered_data directory if it doesn't exist
    args.filtered_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter and copy files
    filter_and_copy_files(args.raw_dir, args.filtered_dir, args.config)

