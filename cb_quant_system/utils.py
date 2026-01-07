"""
工具函数模块
Utility functions for the CB quantitative selection system
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json


def calculate_percentile_rank(series: pd.Series, ascending: bool = True) -> pd.Series:
    """
    计算百分位排名
    Calculate percentile rank for a series
    
    Args:
        series: Pandas Series to rank
        ascending: If True, lower values get lower ranks
        
    Returns:
        Series with percentile ranks (0-100)
    """
    if ascending:
        return series.rank(pct=True) * 100
    else:
        return (1 - series.rank(pct=True)) * 100


def normalize_score(series: pd.Series, method: str = 'minmax') -> pd.Series:
    """
    标准化得分
    Normalize scores using different methods
    
    Args:
        series: Pandas Series to normalize
        method: 'minmax' for min-max normalization, 'zscore' for z-score
        
    Returns:
        Normalized Series
    """
    if method == 'minmax':
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series([50] * len(series), index=series.index)
        return (series - min_val) / (max_val - min_val) * 100
    
    elif method == 'zscore':
        mean_val = series.mean()
        std_val = series.std()
        if std_val == 0:
            return pd.Series([0] * len(series), index=series.index)
        return (series - mean_val) / std_val
    
    return series


def format_number(value: float, decimal_places: int = 2, 
                 suffix: str = '') -> str:
    """
    格式化数字显示
    Format number for display
    
    Args:
        value: Number to format
        decimal_places: Number of decimal places
        suffix: Suffix to add (e.g., '%', '元')
        
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return '-'
    return f"{value:.{decimal_places}f}{suffix}"


def calculate_days_to_maturity(maturity_date: str) -> int:
    """
    计算距离到期日的天数
    Calculate days to maturity
    
    Args:
        maturity_date: Maturity date string (YYYY-MM-DD format)
        
    Returns:
        Days to maturity
    """
    try:
        maturity = datetime.strptime(str(maturity_date)[:10], '%Y-%m-%d')
        today = datetime.now()
        return (maturity - today).days
    except:
        return -1


def classify_rating(rating: str) -> int:
    """
    将评级转换为数值
    Convert rating to numeric value
    
    Args:
        rating: Rating string (e.g., 'AAA', 'AA+', 'AA')
        
    Returns:
        Numeric rating value (higher is better)
    """
    rating_map = {
        'AAA': 100,
        'AA+': 90,
        'AA': 80,
        'AA-': 70,
        'A+': 60,
        'A': 50,
        'A-': 40,
        'BBB+': 30,
        'BBB': 20,
        'BBB-': 10,
    }
    
    if pd.isna(rating):
        return 50  # 默认中等评级
    
    rating_str = str(rating).strip().upper()
    return rating_map.get(rating_str, 50)


def calculate_volatility(prices: pd.Series, window: int = 20) -> float:
    """
    计算价格波动率
    Calculate price volatility
    
    Args:
        prices: Price series
        window: Rolling window size
        
    Returns:
        Annualized volatility
    """
    if len(prices) < window:
        return np.nan
    
    returns = prices.pct_change().dropna()
    volatility = returns.rolling(window=window).std().iloc[-1]
    
    # 年化波动率
    return volatility * np.sqrt(252) * 100


def generate_report(df: pd.DataFrame, strategy_name: str) -> str:
    """
    生成选债报告
    Generate selection report
    
    Args:
        df: Selected bonds DataFrame
        strategy_name: Name of the strategy used
        
    Returns:
        Report string
    """
    report = []
    report.append("=" * 60)
    report.append(f"可转债选债报告 - {strategy_name}")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)
    report.append("")
    
    # 统计信息
    report.append("【统计信息】")
    report.append(f"入选债券数量: {len(df)} 只")
    
    if 'price' in df.columns:
        report.append(f"平均价格: {df['price'].mean():.2f} 元")
    
    if 'premium_rate' in df.columns:
        report.append(f"平均溢价率: {df['premium_rate'].mean():.2f}%")
    
    if 'ytm' in df.columns:
        report.append(f"平均YTM: {df['ytm'].mean():.2f}%")
    
    if 'double_low' in df.columns:
        report.append(f"平均双低值: {df['double_low'].mean():.2f}")
    
    report.append("")
    
    # 评级分布
    if 'rating' in df.columns:
        report.append("【评级分布】")
        rating_dist = df['rating'].value_counts()
        for rating, count in rating_dist.items():
            report.append(f"  {rating}: {count} 只")
        report.append("")
    
    # 债券列表
    report.append("【入选债券】")
    for idx, row in df.iterrows():
        cb_name = row.get('cb_name', 'N/A')
        price = row.get('price', 0)
        premium = row.get('premium_rate', 0)
        report.append(f"  {cb_name}: 价格{price:.2f}, 溢价率{premium:.2f}%")
    
    report.append("")
    report.append("=" * 60)
    report.append("注：以上内容仅供参考，不构成投资建议")
    report.append("=" * 60)
    
    return "\n".join(report)


def export_to_json(df: pd.DataFrame, filename: str) -> bool:
    """
    导出数据到JSON文件
    Export data to JSON file
    
    Args:
        df: DataFrame to export
        filename: Output filename
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # 转换为字典列表
        records = df.to_dict(orient='records')
        
        # 处理NaN值
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"导出JSON失败: {e}")
        return False


def compare_strategies(results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    比较不同策略的选债结果
    Compare selection results from different strategies
    
    Args:
        results: Dict of strategy name to selected DataFrame
        
    Returns:
        Comparison DataFrame
    """
    comparison = []
    
    for strategy_name, df in results.items():
        if len(df) == 0:
            continue
            
        stats = {
            '策略': strategy_name,
            '入选数量': len(df),
        }
        
        if 'price' in df.columns:
            stats['平均价格'] = df['price'].mean()
        
        if 'premium_rate' in df.columns:
            stats['平均溢价率'] = df['premium_rate'].mean()
        
        if 'ytm' in df.columns:
            stats['平均YTM'] = df['ytm'].mean()
        
        if 'double_low' in df.columns:
            stats['平均双低值'] = df['double_low'].mean()
        
        comparison.append(stats)
    
    return pd.DataFrame(comparison)


if __name__ == "__main__":
    # 测试工具函数
    print("测试工具函数...")
    
    # 测试评级转换
    print(f"AAA评级数值: {classify_rating('AAA')}")
    print(f"AA+评级数值: {classify_rating('AA+')}")
    
    # 测试数字格式化
    print(f"格式化数字: {format_number(123.456, 2, '%')}")
    
    # 测试到期天数计算
    future_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    print(f"距离{future_date}还有: {calculate_days_to_maturity(future_date)} 天")
