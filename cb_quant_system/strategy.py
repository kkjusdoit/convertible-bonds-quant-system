"""
选债策略模块
Selection strategy module for convertible bonds
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict
import config


def filter_by_basic_criteria(df: pd.DataFrame,
                            max_premium: float = config.MAX_PREMIUM_RATE,
                            min_ytm: float = config.MIN_YTM,
                            min_volume: float = config.MIN_DAILY_VOLUME,
                            max_price: float = config.MAX_PRICE,
                            min_price: float = config.MIN_PRICE,
                            min_outstanding: float = config.MIN_OUTSTANDING) -> pd.DataFrame:
    """
    基础条件筛选
    Filter bonds by basic criteria
    
    Args:
        df: DataFrame with CB data
        max_premium: Maximum premium rate (%)
        min_ytm: Minimum yield to maturity (%)
        min_volume: Minimum daily volume (万元)
        max_price: Maximum price
        min_price: Minimum price
        min_outstanding: Minimum outstanding amount (亿元)
        
    Returns:
        Filtered DataFrame
    """
    df = df.copy()
    initial_count = len(df)
    
    # 转股溢价率筛选
    if 'premium_rate' in df.columns:
        df = df[df['premium_rate'] <= max_premium]
        print(f"  溢价率 <= {max_premium}%: 剩余 {len(df)} 只")
    
    # 到期收益率筛选
    if 'ytm' in df.columns:
        df = df[df['ytm'] >= min_ytm]
        print(f"  YTM >= {min_ytm}%: 剩余 {len(df)} 只")
    
    # 价格区间筛选
    if 'price' in df.columns:
        df = df[(df['price'] >= min_price) & (df['price'] <= max_price)]
        print(f"  价格在 {min_price}-{max_price}: 剩余 {len(df)} 只")
    
    # 成交额筛选（流动性）
    if 'volume' in df.columns:
        df = df[df['volume'] >= min_volume]
        print(f"  成交额 >= {min_volume}万: 剩余 {len(df)} 只")
    
    # 剩余规模筛选
    if 'outstanding' in df.columns:
        df = df[df['outstanding'] >= min_outstanding]
        print(f"  剩余规模 >= {min_outstanding}亿: 剩余 {len(df)} 只")
    
    print(f"✓ 基础筛选完成: {initial_count} -> {len(df)} 只")
    
    return df


def filter_by_risk(df: pd.DataFrame,
                  filter_st: bool = config.FILTER_ST,
                  filter_forced_redemption: bool = config.FILTER_FORCED_REDEMPTION) -> pd.DataFrame:
    """
    风险过滤
    Filter out high-risk bonds
    
    Args:
        df: DataFrame with CB data
        filter_st: Whether to filter ST stocks
        filter_forced_redemption: Whether to filter bonds with forced redemption announced
        
    Returns:
        Filtered DataFrame
    """
    df = df.copy()
    initial_count = len(df)
    
    # 过滤ST股票对应的转债
    if filter_st and 'stock_name' in df.columns:
        df = df[~df['stock_name'].str.contains('ST|\\*ST', case=False, na=False)]
        print(f"  过滤ST: 剩余 {len(df)} 只")
    
    # 过滤转债名称中包含ST的
    if filter_st and 'cb_name' in df.columns:
        df = df[~df['cb_name'].str.contains('ST', case=False, na=False)]
    
    # 注：强赎过滤需要额外数据源，这里仅作示例
    # 实际使用时可以通过其他字段或数据源判断
    
    print(f"✓ 风险过滤完成: {initial_count} -> {len(df)} 只")
    
    return df


def strategy_low_premium(df: pd.DataFrame, top_n: int = config.TOP_N) -> pd.DataFrame:
    """
    低溢价策略
    Low premium rate strategy - select bonds with lowest premium rates
    
    适合：看好正股上涨，追求进攻性
    
    Args:
        df: DataFrame with CB data
        top_n: Number of top bonds to select
        
    Returns:
        Selected DataFrame sorted by premium rate
    """
    if 'premium_rate' not in df.columns:
        print("✗ 缺少转股溢价率数据")
        return df
    
    result = df.nsmallest(top_n, 'premium_rate')
    print(f"✓ 低溢价策略: 选出 {len(result)} 只")
    
    return result


def strategy_double_low(df: pd.DataFrame, top_n: int = config.TOP_N) -> pd.DataFrame:
    """
    双低策略
    Double-low strategy - select bonds with lowest (price + premium_rate)
    
    适合：追求安全边际和进攻性的平衡
    
    Args:
        df: DataFrame with CB data
        top_n: Number of top bonds to select
        
    Returns:
        Selected DataFrame sorted by double-low value
    """
    if 'double_low' not in df.columns:
        print("✗ 缺少双低值数据")
        return df
    
    result = df.nsmallest(top_n, 'double_low')
    print(f"✓ 双低策略: 选出 {len(result)} 只")
    
    return result


def strategy_high_ytm(df: pd.DataFrame, top_n: int = config.TOP_N) -> pd.DataFrame:
    """
    高收益率策略
    High YTM strategy - select bonds with highest yield to maturity
    
    适合：偏防守，追求债底保护
    
    Args:
        df: DataFrame with CB data
        top_n: Number of top bonds to select
        
    Returns:
        Selected DataFrame sorted by YTM
    """
    if 'ytm' not in df.columns:
        print("✗ 缺少到期收益率数据")
        return df
    
    result = df.nlargest(top_n, 'ytm')
    print(f"✓ 高YTM策略: 选出 {len(result)} 只")
    
    return result


def strategy_composite_score(df: pd.DataFrame, top_n: int = config.TOP_N) -> pd.DataFrame:
    """
    综合评分策略
    Composite score strategy - select bonds with highest composite scores
    
    适合：多因子均衡选债
    
    Args:
        df: DataFrame with CB data
        top_n: Number of top bonds to select
        
    Returns:
        Selected DataFrame sorted by composite score
    """
    if 'composite_score' not in df.columns:
        print("✗ 缺少综合评分数据")
        return df
    
    result = df.nlargest(top_n, 'composite_score')
    print(f"✓ 综合评分策略: 选出 {len(result)} 只")
    
    return result


def strategy_value_hunting(df: pd.DataFrame, top_n: int = config.TOP_N) -> pd.DataFrame:
    """
    价值挖掘策略
    Value hunting strategy - find undervalued bonds
    
    条件：
    - 价格低于105
    - 转股价值高于95
    - 溢价率低于15%
    
    Args:
        df: DataFrame with CB data
        top_n: Number of top bonds to select
        
    Returns:
        Selected DataFrame
    """
    df = df.copy()
    
    conditions = pd.Series([True] * len(df), index=df.index)
    
    if 'price' in df.columns:
        conditions &= (df['price'] < 105)
    
    if 'convert_value' in df.columns:
        conditions &= (df['convert_value'] > 95)
    
    if 'premium_rate' in df.columns:
        conditions &= (df['premium_rate'] < 15)
    
    result = df[conditions]
    
    # 按双低值排序
    if 'double_low' in result.columns and len(result) > 0:
        result = result.nsmallest(min(top_n, len(result)), 'double_low')
    
    print(f"✓ 价值挖掘策略: 选出 {len(result)} 只")
    
    return result


def run_all_strategies(df: pd.DataFrame, top_n: int = config.TOP_N) -> Dict[str, pd.DataFrame]:
    """
    运行所有策略
    Run all selection strategies
    
    Args:
        df: DataFrame with CB data
        top_n: Number of top bonds to select for each strategy
        
    Returns:
        Dict of strategy name to selected DataFrame
    """
    results = {}
    
    print("\n" + "=" * 50)
    print("运行选债策略...")
    print("=" * 50)
    
    results['低溢价策略'] = strategy_low_premium(df, top_n)
    results['双低策略'] = strategy_double_low(df, top_n)
    results['高YTM策略'] = strategy_high_ytm(df, top_n)
    results['综合评分策略'] = strategy_composite_score(df, top_n)
    results['价值挖掘策略'] = strategy_value_hunting(df, top_n)
    
    return results


def format_output(df: pd.DataFrame, 
                 display_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    格式化输出结果
    Format output DataFrame for display
    
    Args:
        df: DataFrame to format
        display_cols: List of columns to display
        
    Returns:
        Formatted DataFrame
    """
    if display_cols is None:
        # 默认显示列
        display_cols = [
            'cb_code', 'cb_name', 'price', 'convert_value', 
            'premium_rate', 'ytm', 'double_low', 'volume',
            'stock_name', 'rating', 'composite_score'
        ]
    
    # 只保留存在的列
    existing_cols = [col for col in display_cols if col in df.columns]
    result = df[existing_cols].copy()
    
    # 格式化数值列
    decimal_cols = ['price', 'convert_value', 'premium_rate', 'ytm', 
                   'double_low', 'composite_score']
    
    for col in decimal_cols:
        if col in result.columns:
            result[col] = result[col].round(config.DECIMAL_PLACES)
    
    return result


if __name__ == "__main__":
    # 测试策略模块
    from data_fetcher import get_cb_data
    from calculator import calculate_all_indicators, calculate_composite_score
    
    df, msg = get_cb_data()
    if df is not None:
        df = calculate_all_indicators(df)
        df = calculate_composite_score(df)
        
        # 基础筛选
        df = filter_by_basic_criteria(df)
        df = filter_by_risk(df)
        
        # 运行策略
        results = run_all_strategies(df)
        
        # 显示综合评分策略结果
        print("\n综合评分策略结果:")
        print(format_output(results['综合评分策略']))
