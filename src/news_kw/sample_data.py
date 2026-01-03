"""Generate sample TXT data for testing."""

from pathlib import Path
from datetime import datetime, timedelta


def generate_sample_data(output_dir: Path):
    """Generate sample TXT news articles.
    
    Args:
        output_dir: Directory to save sample TXT files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample dates
    dates = ['2025-12-15', '2025-12-22', '2025-12-29']
    
    # Sample keywords to repeat
    keywords = ['inflation', 'rate', 'earnings', 'market', 'economy', 
                'growth', 'policy', 'bank', 'trade', 'employment']
    
    # Sample article templates
    templates = [
        """Title: Federal Reserve Considers Interest Rate Changes
Date: {date}
Source: Financial Times

The Federal Reserve is closely monitoring inflation trends as it considers potential interest rate adjustments. Market analysts predict that the central bank may implement policy changes in response to recent economic indicators. Earnings reports from major corporations have shown mixed results, with some sectors experiencing growth while others face challenges.

The economy continues to show resilience despite global trade tensions. Employment figures remain strong, suggesting that the labor market is maintaining its momentum. However, concerns about inflation persist among policymakers.""",

        """Title: Market Volatility and Economic Outlook
Date: {date}
Source: Wall Street Journal

Recent market volatility has raised questions about the sustainability of current economic growth. Inflation concerns have prompted investors to reassess their portfolios, particularly in sectors sensitive to interest rate changes. The Federal Reserve's policy decisions will likely influence market direction in the coming months.

Earnings season has revealed divergent trends across industries. While technology companies report strong earnings, traditional sectors face headwinds. Trade policies continue to impact global supply chains, affecting both domestic and international markets.""",

        """Title: Employment Data and Policy Implications
Date: {date}
Source: Bloomberg

Employment data released this week shows continued strength in the labor market. The unemployment rate remains near historic lows, supporting consumer spending and economic growth. However, wage inflation has become a focal point for policymakers concerned about broader price pressures.

The Federal Reserve faces a delicate balancing act between supporting employment and controlling inflation. Interest rate policy will be critical in managing these competing objectives. Market participants are closely watching for signals about future policy direction.""",

        """Title: Global Trade and Economic Growth
Date: {date}
Source: Reuters

International trade dynamics are shaping the global economic landscape. Trade agreements and tariffs continue to influence market sentiment and corporate earnings. The interconnected nature of modern economies means that policy changes in one region can have far-reaching effects.

Economic growth remains a priority for policymakers worldwide. Central banks are coordinating efforts to manage inflation while supporting sustainable expansion. The balance between growth and stability requires careful policy calibration.""",

        """Title: Banking Sector and Financial Stability
Date: {date}
Source: CNBC

The banking sector faces evolving challenges in the current economic environment. Interest rate changes directly impact bank profitability, as they affect both lending rates and deposit costs. Regulatory policies continue to shape the financial landscape.

Financial stability remains a key concern for central banks. The interplay between monetary policy, market conditions, and regulatory frameworks creates a complex environment for financial institutions. Earnings reports from major banks will provide insights into sector health."""
    ]
    
    # Generate files
    for date in dates:
        date_dir = output_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        for i, template in enumerate(templates):
            article_text = template.format(date=date)
            filename = f"article_{i+1:02d}.txt"
            filepath = date_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(article_text)
    
    print(f"Generated {len(dates) * len(templates)} sample articles in {output_dir}")

