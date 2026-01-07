"""
卡叔2026策略模块
KaShu 2026 Strategy - A comprehensive CB selection strategy

策略来源：卡叔2026年可转债投资策略
四大类转债筛选逻辑：
1. 小市值高溢价距离保本位置不远 - 博弈下修
2. 绝对防御临期债 - 低期权价值、质地安全
3. 大股东未减持 - 可能先下修再减持
4. 存续期2年附近 - 上市公司开始重视促转股
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import config


# ============ 卡叔2026策略参数 ============
KASHU_CONFIG = {
    # 第一类：小市值高溢价
    'type1': {
        'max_outstanding': 3.0,      # 最大剩余规模(亿元)，小市值
        'min_premium_rate': 20.0,    # 最小溢价率(%)，高溢价
        'max_price': 115.0,          # 最大价格，距离保本位置不远
        'min_price': 100.0,          # 最小价格
    },
    # 第二类：绝对防御临期债
    'type2': {
        'max_years': 1.0,            # 最大剩余年限(年)，临期
        'max_price': 105.0,          # 最大价格，接近保本价
        'max_premium_rate': 30.0,    # 最大溢价率，期权价值低
    },
    # 第三类：大股东未减持（需要额外数据，这里用规模变化代替）
    'type3': {
        'min_outstanding': 2.0,      # 最小剩余规模(亿元)，规模未大幅减少
        'max_years': 4.0,            # 最大剩余年限
        'min_years': 1.0,            # 最小剩余年限
    },
    # 第四类：存续期2年附近
    'type4': {
        'min_years': 1.5,            # 最小剩余年限
        'max_years': 2.5,            # 最大剩余年限
        'max_price': 130.0,          # 最大价格
    },
    # 通用过滤
    'common': {
        'min_volume': 50.0,          # 最小成交额(万元)
        'exclude_redeem': True,      # 排除已公告强赎
    }
}


def calculate_distance_to_par(price: float, redemption_price: float = 100.0) -> float:
    """
    计算距离保本价的距离
    Calculate distance to par value (redemption price)
    
    Args:
        price: Current CB price
        redemption_price: Redemption price at maturity (default 100)
        
    Returns:
        Distance to par in percentage
    """
    return ((price - redemption_price) / redemption_price) * 100


def filter_common(df: pd.DataFrame, cfg: dict = KASHU_CONFIG['common']) -> pd.DataFrame:
    """
    通用过滤条件
    Common filters for all types
    """
    df = df.copy()
    
    # 过滤成交额
    if 'volume' in df.columns and cfg.get('min_volume'):
        df = df[df['volume'] >= cfg['min_volume']]
    
    # 排除已公告强赎
    if cfg.get('exclude_redeem') and 'redeem_status' in df.columns:
        df = df[~df['redeem_status'].isin(['已公告强赎', '公告要强赎'])]
    
    # 排除ST
    if 'stock_name' in df.columns:
        df = df[~df['stock_name'].str.contains('ST|\\*ST', case=False, na=False)]
    
    return df


def strategy_type1_small_cap_high_premium(df: pd.DataFrame, 
                                          cfg: dict = KASHU_CONFIG['type1']) -> pd.DataFrame:
    """
    第一类：小市值高溢价距离保本位置不远
    Type 1: Small cap, high premium, close to par value
    
    逻辑：
    - 小市值：剩余规模小，容易被资金推动
    - 高溢价：当前进攻性弱，但下修后可能改善
    - 距离保本位置不远：安全边际
    - 博弈点：下修可能性、存量迷你债爆发
    """
    df = df.copy()
    conditions = pd.Series([True] * len(df), index=df.index)
    
    # 小市值
    if 'outstanding' in df.columns:
        conditions &= (df['outstanding'] <= cfg['max_outstanding'])
    
    # 高溢价
    if 'premium_rate' in df.columns:
        conditions &= (df['premium_rate'] >= cfg['min_premium_rate'])
    
    # 价格区间（距离保本位置不远）
    if 'price' in df.columns:
        conditions &= (df['price'] >= cfg['min_price'])
        conditions &= (df['price'] <= cfg['max_price'])
    
    result = df[conditions].copy()
    
    if len(result) > 0:
        # 计算距离保本价的距离
        result['distance_to_par'] = result['price'].apply(
            lambda x: calculate_distance_to_par(x, 100)
        )
        # 按规模升序排列（越小越好）
        result = result.sort_values('outstanding', ascending=True)
    
    return result


def strategy_type2_defensive_near_maturity(df: pd.DataFrame,
                                           cfg: dict = KASHU_CONFIG['type2']) -> pd.DataFrame:
    """
    第二类：绝对防御，低期权价值、质地安全的临期债
    Type 2: Defensive near-maturity bonds with low option value
    
    逻辑：
    - 临期：剩余年限短，期权价值低
    - 价格接近保本价：安全边际高
    - 博弈点：可能出现保本价以下的价格，博弈小概率事件
    """
    df = df.copy()
    conditions = pd.Series([True] * len(df), index=df.index)
    
    # 临期
    if 'years_to_maturity' in df.columns:
        conditions &= (df['years_to_maturity'] <= cfg['max_years'])
        conditions &= (df['years_to_maturity'] > 0)  # 排除已到期
    
    # 价格接近保本价
    if 'price' in df.columns:
        conditions &= (df['price'] <= cfg['max_price'])
    
    # 溢价率不能太高（期权价值低）
    if 'premium_rate' in df.columns:
        conditions &= (df['premium_rate'] <= cfg['max_premium_rate'])
    
    result = df[conditions].copy()
    
    if len(result) > 0:
        # 计算到期收益率估算
        result['estimated_ytm'] = result.apply(
            lambda x: ((100 - x['price']) / x['price'] / max(x['years_to_maturity'], 0.1)) * 100
            if pd.notna(x['years_to_maturity']) and x['years_to_maturity'] > 0 else 0,
            axis=1
        )
        # 按剩余年限升序排列
        result = result.sort_values('years_to_maturity', ascending=True)
    
    return result


def strategy_type3_major_holder_not_sold(df: pd.DataFrame,
                                         cfg: dict = KASHU_CONFIG['type3']) -> pd.DataFrame:
    """
    第三类：存续期略长，但大股东未减持的转债
    Type 3: Bonds where major shareholders haven't sold
    
    逻辑：
    - 大股东未减持：可能先下修再减持
    - 存续期适中：有足够时间操作
    - 注：由于缺少大股东持仓数据，这里用剩余规模较大作为代理指标
    """
    df = df.copy()
    conditions = pd.Series([True] * len(df), index=df.index)
    
    # 剩余规模较大（代理大股东未大量减持）
    if 'outstanding' in df.columns:
        conditions &= (df['outstanding'] >= cfg['min_outstanding'])
    
    # 存续期适中
    if 'years_to_maturity' in df.columns:
        conditions &= (df['years_to_maturity'] >= cfg['min_years'])
        conditions &= (df['years_to_maturity'] <= cfg['max_years'])
    
    result = df[conditions].copy()
    
    if len(result) > 0:
        # 按剩余规模降序排列（规模大说明减持少）
        result = result.sort_values('outstanding', ascending=False)
    
    return result


def strategy_type4_two_years_maturity(df: pd.DataFrame,
                                      cfg: dict = KASHU_CONFIG['type4']) -> pd.DataFrame:
    """
    第四类：存续期在2年附近的可转债
    Type 4: Bonds with ~2 years to maturity
    
    逻辑：
    - 存续期2年附近：不短不长，上市公司开始重视
    - 期权价值适中：进可攻退可守
    - 博弈点：上市公司可能开始促转股
    """
    df = df.copy()
    conditions = pd.Series([True] * len(df), index=df.index)
    
    # 存续期2年附近
    if 'years_to_maturity' in df.columns:
        conditions &= (df['years_to_maturity'] >= cfg['min_years'])
        conditions &= (df['years_to_maturity'] <= cfg['max_years'])
    
    # 价格不能太高
    if 'price' in df.columns:
        conditions &= (df['price'] <= cfg['max_price'])
    
    result = df[conditions].copy()
    
    if len(result) > 0:
        # 按双低值排序
        if 'double_low' in result.columns:
            result = result.sort_values('double_low', ascending=True)
        elif 'price' in result.columns and 'premium_rate' in result.columns:
            result['double_low'] = result['price'] + result['premium_rate']
            result = result.sort_values('double_low', ascending=True)
    
    return result


def calculate_kashu_score(row: pd.Series) -> float:
    """
    计算卡叔综合评分
    Calculate KaShu composite score
    
    评分逻辑：
    - 规模越小越好（小市值弹性大）
    - 价格越接近100越好（安全边际）
    - 剩余年限适中最好（1.5-2.5年）
    - 溢价率根据策略类型不同评价
    """
    score = 50.0  # 基础分
    
    # 规模评分（越小越好，但不能太小）
    if pd.notna(row.get('outstanding')):
        outstanding = row['outstanding']
        if outstanding < 1:
            score += 10
        elif outstanding < 3:
            score += 15
        elif outstanding < 5:
            score += 10
        elif outstanding < 10:
            score += 5
    
    # 价格评分（越接近100越好）
    if pd.notna(row.get('price')):
        price = row['price']
        if 100 <= price <= 105:
            score += 20
        elif 105 < price <= 110:
            score += 15
        elif 110 < price <= 115:
            score += 10
        elif 115 < price <= 120:
            score += 5
        elif price < 100:
            score += 10  # 折价也加分
    
    # 剩余年限评分（2年附近最好）
    if pd.notna(row.get('years_to_maturity')):
        years = row['years_to_maturity']
        if 1.5 <= years <= 2.5:
            score += 15
        elif 1.0 <= years < 1.5 or 2.5 < years <= 3.0:
            score += 10
        elif 0.5 <= years < 1.0:
            score += 12  # 临期也有价值
        elif years < 0.5:
            score += 8
    
    # 溢价率评分（根据价格区间不同评价）
    if pd.notna(row.get('premium_rate')) and pd.notna(row.get('price')):
        premium = row['premium_rate']
        price = row['price']
        
        if price <= 110:
            # 低价区，高溢价可能有下修机会
            if premium >= 30:
                score += 10
            elif premium >= 20:
                score += 8
        else:
            # 高价区，低溢价更好
            if premium <= 10:
                score += 15
            elif premium <= 20:
                score += 10
    
    return score


def strategy_kashu2026(df: pd.DataFrame, top_n: int = 30) -> Dict[str, pd.DataFrame]:
    """
    卡叔2026综合策略
    KaShu 2026 Comprehensive Strategy
    
    返回四类转债的筛选结果
    
    Args:
        df: DataFrame with CB data
        top_n: Number of top bonds to select for each type
        
    Returns:
        Dict with results for each type
    """
    print("\n" + "=" * 60)
    print("  卡叔2026策略 - KaShu 2026 Strategy")
    print("=" * 60)
    
    # 通用过滤
    df_filtered = filter_common(df)
    print(f"通用过滤后: {len(df_filtered)} 只")
    
    results = {}
    
    # 第一类：小市值高溢价
    print("\n【第一类】小市值高溢价距离保本位置不远")
    type1 = strategy_type1_small_cap_high_premium(df_filtered)
    results['type1_小市值高溢价'] = type1.head(top_n)
    print(f"  筛选结果: {len(type1)} 只")
    
    # 第二类：绝对防御临期债
    print("\n【第二类】绝对防御临期债")
    type2 = strategy_type2_defensive_near_maturity(df_filtered)
    results['type2_防御临期债'] = type2.head(top_n)
    print(f"  筛选结果: {len(type2)} 只")
    
    # 第三类：大股东未减持
    print("\n【第三类】大股东未减持")
    type3 = strategy_type3_major_holder_not_sold(df_filtered)
    results['type3_大股东未减持'] = type3.head(top_n)
    print(f"  筛选结果: {len(type3)} 只")
    
    # 第四类：存续期2年附近
    print("\n【第四类】存续期2年附近")
    type4 = strategy_type4_two_years_maturity(df_filtered)
    results['type4_两年期'] = type4.head(top_n)
    print(f"  筛选结果: {len(type4)} 只")
    
    # 综合评分
    print("\n【综合评分】卡叔2026综合榜")
    df_scored = df_filtered.copy()
    df_scored['kashu_score'] = df_scored.apply(calculate_kashu_score, axis=1)
    df_scored = df_scored.sort_values('kashu_score', ascending=False)
    results['综合评分榜'] = df_scored.head(top_n)
    print(f"  综合评分完成")
    
    return results


def format_kashu_output(df: pd.DataFrame, strategy_type: str) -> pd.DataFrame:
    """
    格式化卡叔策略输出
    Format output for KaShu strategy
    """
    display_cols = [
        'cb_code', 'cb_name', 'price', 'premium_rate', 
        'outstanding', 'years_to_maturity', 'convert_value',
        'stock_name', 'redeem_status'
    ]
    
    # 根据策略类型添加特定列
    if 'kashu_score' in df.columns:
        display_cols.append('kashu_score')
    if 'distance_to_par' in df.columns:
        display_cols.append('distance_to_par')
    if 'estimated_ytm' in df.columns:
        display_cols.append('estimated_ytm')
    if 'double_low' in df.columns:
        display_cols.append('double_low')
    
    existing_cols = [col for col in display_cols if col in df.columns]
    result = df[existing_cols].copy()
    
    # 格式化数值
    for col in ['price', 'premium_rate', 'outstanding', 'years_to_maturity', 
                'convert_value', 'kashu_score', 'distance_to_par', 'estimated_ytm', 'double_low']:
        if col in result.columns:
            result[col] = result[col].round(2)
    
    return result


if __name__ == "__main__":
    # 测试卡叔2026策略
    from data_fetcher import get_cb_data
    from calculator import calculate_all_indicators
    
    df, msg = get_cb_data()
    if df is not None:
        df = calculate_all_indicators(df)
        
        results = strategy_kashu2026(df, top_n=10)
        
        for name, result_df in results.items():
            print(f"\n{'='*60}")
            print(f"  {name}")
            print('='*60)
            if len(result_df) > 0:
                print(format_kashu_output(result_df, name))
            else:
                print("  无符合条件的转债")
