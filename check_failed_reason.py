from pathlib import Path
from src.news_kw.io import parse_date_from_path
from src.news_kw.filter_files import validate_date_parsing

# Test files from failed_date_parsing.txt
test_files = [
    ("data/raw_txt/raddit/2018/Oct_2018 News.docx", "Oct_2018 News.docx"),
    ("data/raw_txt/raddit/2019/2019 News.docx", "2019 News.docx"),
    ("data/raw_txt/raddit/2020/2020 News.docx", "2020 News.docx"),
    ("data/raw_txt/raddit/2021/2021 News(1).docx", "2021 News(1).docx"),
    ("data/raw_txt/raddit/2021/2021 News.docx", "2021 News.docx"),
    ("data/raw_txt/raddit/2022/2022 News(1).docx", "2022 News(1).docx"),
    ("data/raw_txt/raddit/2022/2022 News.docx", "2022 News.docx"),
    ("data/raw_txt/raddit/2022/March_2022.docx", "March_2022.docx"),
    ("data/raw_txt/raddit/2023/2023 News.docx", "2023 News.docx"),
    ("data/raw_txt/raddit/2024/2024 News(1).docx", "2024 News(1).docx"),
    ("data/raw_txt/raddit/2024/2024 News.docx", "2024 News.docx"),
    ("data/raw_txt/raddit/2025/2025 News(1).docx", "2025 News(1).docx"),
    ("data/raw_txt/raddit/2025/2025 News.docx", "2025 News.docx"),
    ("data/raw_txt/raddit/2020/Jun_2020_A few weeks ago, my wife and I saw a post about Solve Oregon helping clean up Portland. Today our group picked up all this in 2 hours! It was so easy to sign up and volunteer. Spread the word! _ r_Portland.pdf", "Jun_2020_..."),
    ("data/raw_txt/raddit/2021/Apr. 15, 2021_Tomorrow - over 800 volunteers signed up to clean Portland BUT one Downtown Project still needs more help... meet at The Standard on 5th Ave. at 10 AM for cleanup supplies and instruction! Sign up below. _ r_Portland.pdf", "Apr. 15, 2021_..."),
    ("data/raw_txt/raddit/2021/_I just want to see things turn around__ Hundreds of volunteers clean up downtown Portland -- Hundreds of volunteers, including Portland Mayor Ted Wheeler, signed up to clean up downtown on Thursday morning. _ r_Portland.pdf", "_I just want..."),
    ("data/raw_txt/raddit/2023/Jul_2023_Get this free weatherization kit, free installation and repairs, free leak repairs, a free water heater, and free home energy retrofitting for income-qualified Portland-area residents (Info in comments) _ r_Portland.pdf", "Jul_2023_..."),
]

print("=" * 80)
print("Checking why files are in failed_date_parsing.txt")
print("=" * 80)

for file_path_str, short_name in test_files:
    file_path = Path(file_path_str)
    
    print(f"\nFile: {short_name}")
    print(f"  Full path: {file_path}")
    print(f"  Exists: {file_path.exists()}")
    
    if file_path.exists():
        # Test date parsing
        parsed_date = parse_date_from_path(file_path)
        validated_date = validate_date_parsing(file_path)
        
        print(f"  parse_date_from_path: {parsed_date}")
        print(f"  validate_date_parsing: {validated_date}")
        
        if parsed_date:
            print(f"  [OK] Date parsing SUCCESS")
        else:
            print(f"  [FAIL] Date parsing FAILED")
    else:
        print(f"  [FAIL] File does NOT exist - this is why it's in failed list!")

