"""
Count files in filtered_data folders and create statistics table.
"""

from pathlib import Path
import pandas as pd

def count_files_in_folders(filtered_dir: Path) -> pd.DataFrame:
    """Count files in each folder under filtered_data.
    
    Args:
        filtered_dir: Path to filtered_data directory
        
    Returns:
        DataFrame with folder names and file counts
    """
    stats = []
    
    for folder in sorted(filtered_dir.iterdir()):
        if folder.is_dir():
            # Count all .txt files recursively
            file_count = len(list(folder.rglob('*.txt')))
            stats.append({
                'Folder': folder.name,
                'File_Count': file_count
            })
            print(f"{folder.name}: {file_count} files")
    
    df = pd.DataFrame(stats)
    return df

def main():
    """Main function."""
    filtered_dir = Path('data/filtered_data')
    output_dir = Path('output/data_statistics')
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Count files
    df = count_files_in_folders(filtered_dir)
    
    # Save to CSV
    output_file = output_dir / 'file_counts.csv'
    df.to_csv(output_file, index=False)
    print(f"\nStatistics saved to: {output_file}")
    
    # Print table
    print("\nFile Count Statistics:")
    print(df.to_string(index=False))

if __name__ == '__main__':
    main()

