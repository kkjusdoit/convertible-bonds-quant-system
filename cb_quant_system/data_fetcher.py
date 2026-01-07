"""
数据获取模块
Data fetching module for convertible bonds using Akshare
"""

import time
import pandas as pd
import numpy as np
import akshare as ak
from typing import Optional, Tuple
import config


def fetch_cb_basic_data(max_retries: int = config.MAX_RETRIES) -> Optional[pd.DataFrame]:
    """
    获取可转债基础数据（实时行情+基本信息）
    Fetch basic CB data including real-time quotes and fundamental info
    
    使用东方财富接口获取全市场可转债数据，无需cookie
    
    Returns:
        DataFrame with CB basic data or None if failed
    """
    for attempt in range(max_retries):
        try:
            # 使用东方财富可转债比价表接口，可获取全市场数据
            df = ak.bond_cov_comparison()
            
            if df is not None and not df.empty:
                print(f"✓ 成功获取 {len(df)} 只可转债数据")
                return df
            
        except Exception as e:
            print(f"✗ 第{attempt + 1}次获取数据失败: {e}")
            if attempt < max_retries - 1:
                print(f"  等待{config.RETRY_INTERVAL}秒后重试...")
                time.sleep(config.RETRY_INTERVAL)
    
    # 备用方案：尝试集思录接口
    print("尝试备用数据源...")
    try:
        df = ak.bond_cb_jsl()
        if df is not None and not df.empty:
            print(f"✓ 备用源获取 {len(df)} 只可转债数据")
            return df
    except Exception as e:
        print(f"✗ 备用源也失败: {e}")
    
    return None


def fetch_cb_realtime_quote() -> Optional[pd.DataFrame]:
    """
    获取可转债实时行情数据（含成交额）
    Fetch real-time quote data including volume/amount
    
    Returns:
        DataFrame with real-time quote data
    """
    try:
        df = ak.bond_zh_hs_cov_spot()
        if df is not None and not df.empty:
            # 标准化列名
            df = df.rename(columns={
                'code': 'cb_code',
                'name': 'cb_name_rt',
                'trade': 'price_rt',
                'volume': 'volume_shares',  # 成交量（股）
                'amount': 'volume',         # 成交额（元）
                'changepercent': 'change_pct_rt',
                'high': 'high',
                'low': 'low',
                'open': 'open',
            })
            # 成交额转换为万元
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce') / 10000
            print(f"✓ 获取实时行情 {len(df)} 条")
            return df[['cb_code', 'volume', 'high', 'low', 'open']]
    except Exception as e:
        print(f"✗ 获取实时行情失败: {e}")
    return None


def fetch_cb_redeem_data() -> Optional[pd.DataFrame]:
    """
    获取可转债强赎数据（含剩余规模、到期日、强赎状态）
    Fetch CB redemption data including outstanding, maturity date, redemption status
    
    Returns:
        DataFrame with redemption related data
    """
    try:
        df = ak.bond_cb_redeem_jsl()
        if df is not None and not df.empty:
            df = df.rename(columns={
                '代码': 'cb_code',
                '名称': 'cb_name_redeem',
                '剩余规模': 'outstanding',
                '到期日': 'maturity_date',
                '强赎状态': 'redeem_status',
                '转股起始日': 'convert_start_date',
                '最后交易日': 'last_trade_date',
            })
            print(f"✓ 获取强赎数据 {len(df)} 条")
            return df[['cb_code', 'outstanding', 'maturity_date', 'redeem_status', 
                      'convert_start_date', 'last_trade_date']]
    except Exception as e:
        print(f"✗ 获取强赎数据失败: {e}")
    return None


def fetch_cb_index_data() -> Optional[pd.DataFrame]:
    """
    获取可转债指数数据（可选，用于市场整体分析）
    Fetch CB index data for market overview
    
    Returns:
        DataFrame with CB index data or None if failed
    """
    try:
        # 获取中证转债指数
        df = ak.bond_zh_hs_cov_daily(symbol="sz399413")
        if df is not None and not df.empty:
            print(f"✓ 成功获取转债指数数据")
            return df
    except Exception as e:
        print(f"✗ 获取转债指数数据失败: {e}")
    
    return None


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化列名，统一数据格式
    Standardize column names and data formats
    
    Args:
        df: Raw DataFrame from data source
        
    Returns:
        DataFrame with standardized column names
    """
    # 东方财富接口 + 集思录接口的列名映射
    column_mapping = {
        # 东方财富接口字段
        '转债代码': 'cb_code',
        '转债名称': 'cb_name',
        '转债最新价': 'price',
        '转债涨跌幅': 'change_pct',
        '转股价值': 'convert_value',
        '转股溢价率': 'premium_rate',
        '纯债价值': 'pure_bond_value',
        '纯债溢价率': 'pure_bond_premium',
        '正股代码': 'stock_code',
        '正股名称': 'stock_name',
        '正股最新价': 'stock_price',
        '正股涨跌幅': 'stock_change_pct',
        '转股价': 'convert_price',
        '回售触发价': 'put_trigger_price',
        '强赎触发价': 'call_trigger_price',
        '到期赎回价': 'redemption_price',
        '开始转股日': 'convert_start_date',
        '上市日期': 'list_date',
        '申购日期': 'ipo_date',
        # 集思录接口字段（备用）
        '现价': 'price',
        '涨跌幅': 'change_pct',
        '到期收益率': 'ytm',
        '剩余年限': 'years_to_maturity',
        '剩余规模': 'outstanding',
        '成交额': 'volume',
        '正股价': 'stock_price',
        '双低': 'double_low',
        '评级': 'rating',
        '到期时间': 'maturity_date',
    }
    
    # 重命名存在的列
    existing_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df.rename(columns=existing_cols)
    
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗数据，处理缺失值和异常值
    Clean data by handling missing values and outliers
    
    Args:
        df: DataFrame to clean
        
    Returns:
        Cleaned DataFrame
    """
    # 复制数据避免修改原始数据
    df = df.copy()
    
    # 定义数值列
    numeric_cols = ['price', 'convert_value', 'premium_rate', 'pure_bond_value',
                    'ytm', 'years_to_maturity', 'outstanding', 'volume',
                    'stock_price', 'convert_price', 'double_low']
    
    # 转换数值列
    for col in numeric_cols:
        if col in df.columns:
            # 处理百分号和其他非数值字符
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('%', '').str.replace(',', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 过滤掉价格为空或为0的记录
    if 'price' in df.columns:
        df = df[df['price'].notna() & (df['price'] > 0)]
    
    # 过滤掉转股溢价率为空的记录
    if 'premium_rate' in df.columns:
        df = df[df['premium_rate'].notna()]
    
    print(f"✓ 数据清洗完成，剩余 {len(df)} 条有效记录")
    
    return df


def get_cb_data() -> Tuple[Optional[pd.DataFrame], str]:
    """
    获取并处理可转债数据的主函数
    Main function to fetch and process CB data
    
    Returns:
        Tuple of (processed DataFrame, status message)
    """
    print("=" * 50)
    print("开始获取可转债数据...")
    print("=" * 50)
    
    # 获取基础数据（东方财富比价表）
    df = fetch_cb_basic_data()
    
    if df is None:
        return None, "获取数据失败，请检查网络连接或稍后重试"
    
    # 标准化列名
    df = standardize_columns(df)
    
    # 获取实时行情数据（含成交额）
    rt_df = fetch_cb_realtime_quote()
    if rt_df is not None:
        df['cb_code'] = df['cb_code'].astype(str)
        rt_df['cb_code'] = rt_df['cb_code'].astype(str)
        df = df.merge(rt_df, on='cb_code', how='left')
    
    # 获取强赎数据（含剩余规模、到期日）
    redeem_df = fetch_cb_redeem_data()
    if redeem_df is not None:
        redeem_df['cb_code'] = redeem_df['cb_code'].astype(str)
        df = df.merge(redeem_df, on='cb_code', how='left')
    
    # 清洗数据
    df = clean_data(df)
    
    # 计算剩余年限
    if 'maturity_date' in df.columns:
        df['maturity_date'] = pd.to_datetime(df['maturity_date'], errors='coerce')
        df['years_to_maturity'] = (df['maturity_date'] - pd.Timestamp.now()).dt.days / 365
        df['years_to_maturity'] = df['years_to_maturity'].round(2)
    
    if df.empty:
        return None, "清洗后无有效数据"
    
    return df, "数据获取成功"


if __name__ == "__main__":
    # 测试数据获取
    df, msg = get_cb_data()
    if df is not None:
        print("\n数据预览:")
        print(df.head(10))
        print(f"\n列名: {df.columns.tolist()}")
    else:
        print(msg)
