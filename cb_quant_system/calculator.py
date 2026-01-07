"""
指标计算模块
Indicator calculation module for convertible bonds
"""

import pandas as pd
import numpy as np
from typing import Optional
import config


def calculate_convert_value(stock_price: float, convert_price: float, 
                           face_value: float = 100.0) -> float:
    """
    计算转股价值
    Calculate conversion value
    
    转股价值 = 正股价格 / 转股价格 * 面值
    
    Args:
        stock_price: Current stock price
        convert_price: Conversion price
        face_value: Bond face value (default 100)
        
    Returns:
        Conversion value
    """
    if convert_price <= 0 or pd.isna(convert_price):
        return np.nan
    return (stock_price / convert_price) * face_value


def calculate_premium_rate(cb_price: float, convert_value: float) -> float:
    """
    计算转股溢价率
    Calculate conversion premium rate
    
    转股溢价率 = (转债价格 - 转股价值) / 转股价值 * 100%
    
    Args:
        cb_price: Convertible bond price
        convert_value: Conversion value
        
    Returns:
        Premium rate in percentage
    """
    if convert_value <= 0 or pd.isna(convert_value):
        return np.nan
    return ((cb_price - convert_value) / convert_value) * 100


def calculate_double_low(price: float, premium_rate: float,
                        coefficient: float = config.DOUBLE_LOW_COEFFICIENT) -> float:
    """
    计算双低值
    Calculate double-low value
    
    双低值 = 转债价格 + 转股溢价率 * 系数
    双低值越低，说明价格低且溢价率低，性价比越高
    
    Args:
        price: CB price
        premium_rate: Premium rate in percentage
        coefficient: Weight coefficient for premium rate
        
    Returns:
        Double-low value
    """
    if pd.isna(price) or pd.isna(premium_rate):
        return np.nan
    return price + premium_rate * coefficient


def calculate_pure_bond_value(face_value: float, coupon_rate: float,
                             years_to_maturity: float, 
                             discount_rate: float = 0.04) -> float:
    """
    计算纯债价值（简化模型）
    Calculate pure bond value using simplified model
    
    使用现金流折现模型估算纯债价值
    
    Args:
        face_value: Bond face value
        coupon_rate: Annual coupon rate
        years_to_maturity: Years to maturity
        discount_rate: Discount rate (default 4%)
        
    Returns:
        Pure bond value
    """
    if years_to_maturity <= 0:
        return face_value
    
    # 简化计算：假设每年付息一次
    pv = 0
    annual_coupon = face_value * coupon_rate
    
    for year in range(1, int(years_to_maturity) + 1):
        pv += annual_coupon / ((1 + discount_rate) ** year)
    
    # 最后一年加上本金
    pv += face_value / ((1 + discount_rate) ** years_to_maturity)
    
    return pv


def calculate_ytm_simple(price: float, face_value: float, 
                        years_to_maturity: float,
                        coupon_rate: float = 0.01) -> float:
    """
    简化计算到期收益率
    Calculate simplified yield to maturity
    
    使用简化公式估算YTM
    YTM ≈ (年息 + (面值-现价)/剩余年限) / ((面值+现价)/2)
    
    Args:
        price: Current CB price
        face_value: Bond face value (usually 100)
        years_to_maturity: Years to maturity
        coupon_rate: Annual coupon rate
        
    Returns:
        YTM in percentage
    """
    if years_to_maturity <= 0 or price <= 0:
        return np.nan
    
    annual_coupon = face_value * coupon_rate
    capital_gain = (face_value - price) / years_to_maturity
    average_price = (face_value + price) / 2
    
    ytm = (annual_coupon + capital_gain) / average_price * 100
    return ytm


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有指标
    Calculate all indicators for the CB DataFrame
    
    Args:
        df: DataFrame with basic CB data
        
    Returns:
        DataFrame with calculated indicators
    """
    df = df.copy()
    
    # 如果转股价值不存在，则计算
    if 'convert_value' not in df.columns or df['convert_value'].isna().all():
        if 'stock_price' in df.columns and 'convert_price' in df.columns:
            df['convert_value'] = df.apply(
                lambda x: calculate_convert_value(x['stock_price'], x['convert_price']),
                axis=1
            )
            print("✓ 已计算转股价值")
    
    # 如果转股溢价率不存在，则计算
    if 'premium_rate' not in df.columns or df['premium_rate'].isna().all():
        if 'price' in df.columns and 'convert_value' in df.columns:
            df['premium_rate'] = df.apply(
                lambda x: calculate_premium_rate(x['price'], x['convert_value']),
                axis=1
            )
            print("✓ 已计算转股溢价率")
    
    # 如果双低值不存在，则计算
    if 'double_low' not in df.columns or df['double_low'].isna().all():
        if 'price' in df.columns and 'premium_rate' in df.columns:
            df['double_low'] = df.apply(
                lambda x: calculate_double_low(x['price'], x['premium_rate']),
                axis=1
            )
            print("✓ 已计算双低值")
    
    # 计算价格偏离度（相对于100元面值）
    if 'price' in df.columns:
        df['price_deviation'] = (df['price'] - 100) / 100 * 100
    
    # 计算转股价值偏离度
    if 'convert_value' in df.columns:
        df['cv_deviation'] = (df['convert_value'] - 100) / 100 * 100
    
    # 计算溢价率排名（百分位）
    if 'premium_rate' in df.columns:
        df['premium_rank_pct'] = df['premium_rate'].rank(pct=True) * 100
    
    # 计算双低排名（百分位）
    if 'double_low' in df.columns:
        df['double_low_rank_pct'] = df['double_low'].rank(pct=True) * 100
    
    print("✓ 指标计算完成")
    
    return df


def calculate_composite_score(df: pd.DataFrame, 
                             weights: dict = config.WEIGHTS) -> pd.DataFrame:
    """
    计算综合评分
    Calculate composite score based on multiple factors
    
    评分逻辑：
    - 转股溢价率：越低越好，取反向排名
    - 到期收益率：越高越好，取正向排名
    - 双低值：越低越好，取反向排名
    - 转股价值：越高越好，取正向排名
    
    Args:
        df: DataFrame with calculated indicators
        weights: Dict of factor weights
        
    Returns:
        DataFrame with composite scores
    """
    df = df.copy()
    
    # 计算各因子的标准化得分（0-100分）
    scores = pd.DataFrame(index=df.index)
    
    # 转股溢价率得分（越低越好）
    if 'premium_rate' in df.columns and weights.get('premium_rate', 0) > 0:
        # 使用排名百分位，反向（低溢价率得高分）
        scores['premium_score'] = (1 - df['premium_rate'].rank(pct=True)) * 100
    
    # 到期收益率得分（越高越好）
    if 'ytm' in df.columns and weights.get('ytm', 0) > 0:
        scores['ytm_score'] = df['ytm'].rank(pct=True) * 100
    
    # 双低值得分（越低越好）
    if 'double_low' in df.columns and weights.get('double_low', 0) > 0:
        scores['double_low_score'] = (1 - df['double_low'].rank(pct=True)) * 100
    
    # 转股价值得分（越高越好）
    if 'convert_value' in df.columns and weights.get('convert_value', 0) > 0:
        scores['cv_score'] = df['convert_value'].rank(pct=True) * 100
    
    # 计算加权综合得分
    composite_score = 0
    
    if 'premium_score' in scores.columns:
        composite_score += scores['premium_score'] * weights.get('premium_rate', 0)
    
    if 'ytm_score' in scores.columns:
        composite_score += scores['ytm_score'] * weights.get('ytm', 0)
    
    if 'double_low_score' in scores.columns:
        composite_score += scores['double_low_score'] * weights.get('double_low', 0)
    
    if 'cv_score' in scores.columns:
        composite_score += scores['cv_score'] * weights.get('convert_value', 0)
    
    df['composite_score'] = composite_score
    
    # 添加各因子得分到结果中
    for col in scores.columns:
        df[col] = scores[col]
    
    print("✓ 综合评分计算完成")
    
    return df


if __name__ == "__main__":
    # 测试计算模块
    from data_fetcher import get_cb_data
    
    df, msg = get_cb_data()
    if df is not None:
        df = calculate_all_indicators(df)
        df = calculate_composite_score(df)
        print("\n计算结果预览:")
        print(df[['cb_name', 'price', 'premium_rate', 'double_low', 'composite_score']].head(10))
