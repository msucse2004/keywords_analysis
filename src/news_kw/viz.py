"""Python visualization for preview figures."""

import warnings
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from wordcloud import WordCloud
import numpy as np
from scipy.interpolate import make_interp_spline
from news_kw.config import Config


def plot_keyword_trends(topn_by_date_path: Path, config: Config, output_path: Path):
    """Plot keyword trends over time using keyword_topn_by_date.csv.
    
    Reads the Top N by date CSV file and plots frequency over time with a smoothing curve.
    Each rank gets its own colored line, and each point is labeled with its token.
    
    Args:
        topn_by_date_path: Path to keyword_topn_by_date.csv (columns: date, rank, token, freq, freq_norm)
        config: Configuration object
        output_path: Path to save figure
    """
    try:
        # Read the Top N by date CSV
        df = pd.read_csv(topn_by_date_path)
        df['date'] = pd.to_datetime(df['date'])
        
        # Filter to Top N ranks (1 to TREND_PLOT_TOP_N)
        df_filtered = df[df['rank'] <= config.TREND_PLOT_TOP_N].copy()
        
        if len(df_filtered) == 0:
            warnings.warn("No data points to plot")
            return
        
        # Define colors for each rank (using viridis-like colors)
        colors = plt.cm.viridis(np.linspace(0.2, 0.9, config.TREND_PLOT_TOP_N))
        rank_colors = {rank: colors[rank - 1] for rank in range(1, config.TREND_PLOT_TOP_N + 1)}
        
        # Plot
        plt.figure(figsize=(14, 7))
        ax = plt.gca()
        
        # Process each rank separately (need to get data range first)
        for rank in range(1, config.TREND_PLOT_TOP_N + 1):
            df_rank = df_filtered[df_filtered['rank'] == rank].copy()
            
            if len(df_rank) == 0:
                continue
            
            # Sort by date
            df_rank = df_rank.sort_values('date')
            
            # Extract data for plotting
            plot_dates = pd.to_datetime(df_rank['date'].values)
            plot_freqs = df_rank['freq'].values
            plot_labels = df_rank['token'].values
            
            # Convert dates to numeric for interpolation
            date_numeric = np.array([pd.Timestamp(d).timestamp() for d in plot_dates])
            
            # Create smoothing curve using spline interpolation
            if len(plot_dates) > 2:
                # Create more points for smooth curve
                date_numeric_smooth = np.linspace(date_numeric.min(), date_numeric.max(), 300)
                spline = make_interp_spline(date_numeric, plot_freqs, k=min(3, len(plot_dates)-1))
                freq_smooth = spline(date_numeric_smooth)
                # Clip negative values to 0 to prevent curve from going below 0
                freq_smooth = np.clip(freq_smooth, 0, None)
                date_smooth = pd.to_datetime(date_numeric_smooth, unit='s')
            else:
                # If too few points, just use original
                date_smooth = plot_dates
                freq_smooth = plot_freqs
                # Clip negative values to 0
                freq_smooth = np.clip(freq_smooth, 0, None)
            
            color = rank_colors[rank]
            
            # Plot smoothing curve for this rank
            plt.plot(
                date_smooth,
                freq_smooth,
                color=color,
                linewidth=2.5,
                alpha=0.7,
                linestyle='-',
                zorder=1,
                label=f'Rank {rank}',
                clip_on=True
            )
            
            # Plot points for this rank
            plt.scatter(
                plot_dates,
                plot_freqs,
                color=color,
                s=100,
                alpha=0.9,
                zorder=3,
                edgecolors='white',
                linewidths=2
            )
            
            # Add labels at each point (using token)
            for date, freq, token in zip(plot_dates, plot_freqs, plot_labels):
                plt.annotate(
                    token,
                    xy=(date, freq),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=8,
                    color='black',
                    fontweight='bold',
                    alpha=0.9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, edgecolor=color, linewidth=1.5),
                    zorder=4
                )
        
        plt.xlabel('Date', fontsize=12, fontweight='bold')
        plt.ylabel('Frequency', fontsize=12, fontweight='bold')
        plt.title(f'Top {config.TREND_PLOT_TOP_N} Keywords by Date', 
                 fontsize=14, fontweight='bold', pad=20)
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.tight_layout()
        
        # Set y-axis: minimum is 0, maximum is automatically set by matplotlib based on data
        # Get current limits and ensure minimum is 0, maximum is preserved or auto-set
        y_min, y_max = ax.get_ylim()
        ax.set_ylim(bottom=0, top=None)  # None means auto-scale to fit data
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
    except Exception as e:
        warnings.warn(f"Failed to create keyword trends plot: {e}")


def plot_keyword_map(nodes_path: Path, edges_path: Path, config: Config, output_path: Path):
    """Plot keyword co-occurrence network map.
    
    Args:
        nodes_path: Path to cooccurrence_nodes.csv
        edges_path: Path to cooccurrence_edges.csv
        config: Configuration object
        output_path: Path to save figure
    """
    try:
        nodes_df = pd.read_csv(nodes_path)
        edges_df = pd.read_csv(edges_path)
        
        # Create graph
        G = nx.Graph()
        
        # Add nodes
        for _, row in nodes_df.iterrows():
            G.add_node(row['token'], doc_freq=row['doc_freq'])
        
        # Add edges
        for _, row in edges_df.iterrows():
            G.add_edge(row['source'], row['target'], weight=row['weight'])
        
        # Layout
        pos = nx.spring_layout(G, seed=42, k=1, iterations=50)
        
        # Plot
        plt.figure(figsize=(14, 10))
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, alpha=0.2, width=0.5)
        
        # Draw nodes
        node_sizes = [nodes_df[nodes_df['token'] == node]['doc_freq'].values[0] * 10 
                     for node in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='lightblue', alpha=0.7)
        
        # Draw labels (top N by doc_freq)
        top_label_tokens = nodes_df.head(config.COOC_LABEL_TOP_N)['token'].tolist()
        labels = {node: node if node in top_label_tokens else '' for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=6, font_weight='bold')
        
        plt.title(f'Keyword Co-occurrence Network (Top {config.COOC_NODE_TOP_N} nodes, Top {config.COOC_EDGE_TOP_N} edges)')
        plt.axis('off')
        plt.tight_layout()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
    except Exception as e:
        warnings.warn(f"Failed to create keyword map plot: {e}")


def plot_wordcloud_python(config: Config, keyword_topk_csv: Path, exclude_keywords: list, output_path: Path):
    """Plot word cloud from keyword frequencies.
    
    Args:
        config: Configuration object
        keyword_topk_csv: Path to keyword_topk.csv (token, freq)
        exclude_keywords: List of keywords to exclude
        output_path: Path to save figure
    """
    try:
        # Read keyword data
        df = pd.read_csv(keyword_topk_csv)
        
        # Filter out excluded keywords (case-insensitive)
        if exclude_keywords:
            exclude_set = {kw.lower() for kw in exclude_keywords}
            df = df[~df['token'].str.lower().isin(exclude_set)].copy()
        
        # Filter to top N keywords
        df_top = df.head(config.WORDCLOUD_TOP_N)
        
        # Convert to frequency dictionary
        freq_dict = dict(zip(df_top['token'], df_top['freq']))
        
        # Create word cloud
        wordcloud = WordCloud(
            width=config.WORDCLOUD_WIDTH,
            height=config.WORDCLOUD_HEIGHT,
            background_color=config.WORDCLOUD_BACKGROUND,
            max_words=config.WORDCLOUD_MAX_WORDS,
            relative_scaling=0.5,
            colormap='viridis'
        ).generate_from_frequencies(freq_dict)
        
        # Plot
        plt.figure(figsize=(14, 9))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.tight_layout(pad=0)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0)
        plt.close()
        
    except Exception as e:
        warnings.warn(f"Failed to create word cloud plot: {e}")

