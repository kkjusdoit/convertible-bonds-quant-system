"""
盛唐策略模块
ShengTang Strategy - Professional CB Valuation Model

策略来源：盛唐风物的可转债估值方法
核心公式：转债估值 = max(到期折现,回售折现) + 正常转股认购价值 + 下修转股组合期权价值 – 强赎认购损失

五大组成部分：
1. 到期折现（债底）- 用信用债利率折现，考虑转股概率修正
2. 回售折现 - 考虑回售触发概率
3. 正常转股认购价值 - BS模型计算
4. 下修转股组合期权价值 - 下修-转股联合过程估值
5. 强赎认购损失 - 强赎导致的期权价值损失
"""

import pandas as pd
import numpy as np
from scipy.stats import norm
from scipy.integrate import quad
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
import math


# ============ 盛唐策略参数 ============
SHENGTANG_CONFIG = {
    # 无风险利率（年化）
    'risk_free_rate': 0.025,
    
    # 信用利差（根据评级）
    'credit_spread': {
        'AAA': 0.005,
        'AA+': 0.010,
        'AA': 0.015,
        'AA-': 0.020,
        'A+': 0.030,
        'A': 0.040,
        'A-': 0.050,
        'BBB': 0.070,
        'default': 0.025,
    },
    
    # 强赎触发价格（相对转股价）
    'call_trigger_ratio': 1.30,
    
    # 回售触发价格（相对转股价）
    'put_trigger_ratio': 0.70,
    
    # 下修触发概率基准
    'downward_revision_base_prob': 0.80,
    
    # 历史波动率修正系数（转债发行后波动率往往增大）
    'volatility_adjustment': 1.1,
    
    # 默认波动率（如果无法获取历史数据）
    'default_volatility': 0.35,
    
    # 转股概率阈值（平价超过130元）
    'conversion_threshold': 130.0,
}


def black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Black-Scholes 欧式看涨期权定价
    
    Args:
        S: 标的资产当前价格（正股价）
        K: 行权价格（转股价）
        T: 到期时间（年）
        r: 无风险利率
        sigma: 波动率
        
    Returns:
        期权价值
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(0, S - K)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    return max(0, call_price)


def black_scholes_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Black-Scholes 欧式看跌期权定价
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(0, K - S)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    put_price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return max(0, put_price)


def get_credit_spread(rating: str) -> float:
    """
    根据评级获取信用利差
    """
    if pd.isna(rating):
        return SHENGTANG_CONFIG['credit_spread']['default']
    
    rating_str = str(rating).strip().upper()
    return SHENGTANG_CONFIG['credit_spread'].get(
        rating_str, 
        SHENGTANG_CONFIG['credit_spread']['default']
    )


def calculate_conversion_probability(S: float, K: float, T: float, 
                                    sigma: float, threshold: float = 130.0) -> float:
    """
    计算转股概率（平价超过阈值的概率）
    
    使用对数正态分布计算股价超过某阈值的概率
    
    Args:
        S: 当前正股价
        K: 转股价
        T: 剩余时间（年）
        sigma: 波动率
        threshold: 转股价值阈值（默认130）
        
    Returns:
        转股概率
    """
    if T <= 0 or sigma <= 0:
        # 已到期，直接判断当前是否满足
        current_cv = (S / K) * 100
        return 1.0 if current_cv >= threshold else 0.0
    
    # 需要正股价达到的水平
    required_stock_price = K * threshold / 100
    
    # 使用对数正态分布
    r = SHENGTANG_CONFIG['risk_free_rate']
    d2 = (np.log(S / required_stock_price) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    prob = norm.cdf(d2)
    
    return prob


def calculate_bond_floor(face_value: float, coupon_rates: list, 
                        years_to_maturity: float, discount_rate: float,
                        conversion_probs: list = None) -> float:
    """
    计算债底（到期折现值）
    
    改进点：
    1. 使用信用债利率折现（包含违约风险）
    2. 考虑转股概率修正（转股导致利息损失）
    
    Args:
        face_value: 面值
        coupon_rates: 各年票息率列表
        years_to_maturity: 剩余年限
        discount_rate: 折现率（含信用利差）
        conversion_probs: 各期转股概率列表
        
    Returns:
        债底价值
    """
    if years_to_maturity <= 0:
        return face_value
    
    # 简化处理：假设每年付息一次
    n_years = int(np.ceil(years_to_maturity))
    
    # 如果没有提供票息率，使用默认值
    if coupon_rates is None or len(coupon_rates) == 0:
        # 典型可转债票息结构：0.4%, 0.6%, 1.0%, 1.5%, 2.0%, 2.5%
        coupon_rates = [0.004, 0.006, 0.010, 0.015, 0.020, 0.025]
    
    # 如果没有提供转股概率，假设为0
    if conversion_probs is None:
        conversion_probs = [0.0] * n_years
    
    pv = 0
    remaining_prob = 1.0  # 剩余未转股概率
    
    for year in range(1, n_years + 1):
        if year > years_to_maturity:
            break
            
        # 当期票息
        coupon_idx = min(year - 1, len(coupon_rates) - 1)
        coupon = face_value * coupon_rates[coupon_idx]
        
        # 当期转股概率
        conv_prob_idx = min(year - 1, len(conversion_probs) - 1)
        conv_prob = conversion_probs[conv_prob_idx]
        
        # 考虑转股概率修正后的现金流
        adjusted_coupon = coupon * remaining_prob * (1 - conv_prob)
        
        # 折现
        pv += adjusted_coupon / ((1 + discount_rate) ** year)
        
        # 更新剩余未转股概率
        remaining_prob *= (1 - conv_prob)
    
    # 最后一期加上本金（考虑转股概率）
    pv += face_value * remaining_prob / ((1 + discount_rate) ** years_to_maturity)
    
    return pv


def calculate_put_value(face_value: float, put_price: float,
                       years_to_put: float, discount_rate: float,
                       put_probability: float = 0.1) -> float:
    """
    计算回售价值
    
    注意：回售实际触发概率很低（历史上约10%），需要用系数修正
    
    Args:
        face_value: 面值
        put_price: 回售价格
        years_to_put: 距离回售期的时间
        discount_rate: 折现率
        put_probability: 回售触发概率
        
    Returns:
        回售折现价值
    """
    if years_to_put <= 0:
        return put_price * put_probability
    
    # 回售价值 = 回售价格折现 * 触发概率
    put_pv = put_price / ((1 + discount_rate) ** years_to_put)
    
    return put_pv * put_probability


def calculate_call_option_value(S: float, K: float, T: float, 
                               sigma: float, r: float) -> float:
    """
    计算正常转股认购价值
    
    使用BS模型，需要用下修概率修正以避免重复计算
    
    Args:
        S: 正股价
        K: 转股价
        T: 剩余时间
        sigma: 波动率
        r: 无风险利率
        
    Returns:
        转股期权价值（每张转债，面值100元）
    """
    # 每张转债可转换的股数
    shares_per_bond = 100 / K
    
    # 单股期权价值
    call_value = black_scholes_call(S, K, T, r, sigma)
    
    # 转债的转股期权价值
    return call_value * shares_per_bond


def calculate_downward_revision_value(S: float, K: float, T: float,
                                     sigma: float, r: float,
                                     years_to_put: float) -> float:
    """
    计算下修转股组合期权价值
    
    下修-转股是一个连续过程：
    1. 下修主要在回售期前1年和回售期内触发
    2. 下修后转股价降低，转股价值提升
    3. 需要对时间积分计算组合期权价值
    
    Args:
        S: 正股价
        K: 当前转股价
        T: 剩余年限
        sigma: 波动率
        r: 无风险利率
        years_to_put: 距离回售期的时间
        
    Returns:
        下修转股组合期权价值
    """
    # 下修触发概率（回售期前1年和回售期内约80%）
    base_prob = SHENGTANG_CONFIG['downward_revision_base_prob']
    
    # 根据距离回售期的时间调整概率
    if years_to_put <= 0:
        # 已在回售期内
        revision_prob = base_prob
    elif years_to_put <= 1:
        # 回售期前1年
        revision_prob = base_prob * 0.9
    elif years_to_put <= 2:
        revision_prob = base_prob * 0.5
    else:
        revision_prob = base_prob * 0.2
    
    # 如果当前已经是深度价内，下修概率降低
    current_cv = (S / K) * 100
    if current_cv > 100:
        revision_prob *= 0.3
    elif current_cv > 90:
        revision_prob *= 0.6
    
    # 假设下修后转股价降至当前股价的90%
    new_K = S * 0.9
    
    # 下修后的期权价值增量
    original_call = calculate_call_option_value(S, K, T, sigma, r)
    revised_call = calculate_call_option_value(S, new_K, T, sigma, r)
    
    value_increase = max(0, revised_call - original_call)
    
    return value_increase * revision_prob


def calculate_forced_redemption_loss(S: float, K: float, T: float,
                                    sigma: float, r: float,
                                    call_trigger: float = 1.30) -> float:
    """
    计算强赎认购损失
    
    强赎会导致期权价值损失，因为持有人被迫提前转股
    
    Args:
        S: 正股价
        K: 转股价
        T: 剩余时间
        sigma: 波动率
        r: 无风险利率
        call_trigger: 强赎触发比例（默认130%）
        
    Returns:
        强赎导致的期权价值损失
    """
    if T <= 0.5:  # 临期转债强赎影响小
        return 0
    
    # 强赎触发价格
    call_price = K * call_trigger
    
    # 计算强赎概率（股价超过强赎触发价的概率）
    d2 = (np.log(S / call_price) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    call_prob = norm.cdf(d2)
    
    # 如果当前已经接近强赎，概率更高
    current_cv = (S / K) * 100
    if current_cv > 125:
        call_prob = min(0.95, call_prob * 1.5)
    
    # 强赎损失 = 剩余期权时间价值 * 强赎概率
    # 假设强赎发生在1年后
    remaining_T = max(0, T - 1)
    
    if remaining_T > 0:
        # 正常持有到期的期权价值
        full_option = calculate_call_option_value(S, K, T, sigma, r)
        # 强赎后（1年后）的期权价值
        early_option = calculate_call_option_value(S, K, 1, sigma, r)
        
        loss = max(0, full_option - early_option) * call_prob
    else:
        loss = 0
    
    return loss


def calculate_shengtang_value(row: pd.Series, 
                             config: dict = SHENGTANG_CONFIG) -> dict:
    """
    计算盛唐估值
    
    核心公式：
    转债估值 = max(到期折现,回售折现) + 正常转股认购价值 + 下修转股组合期权价值 – 强赎认购损失
    
    Args:
        row: 单只转债的数据行
        config: 配置参数
        
    Returns:
        包含各部分估值的字典
    """
    result = {
        'bond_floor': 0,           # 债底
        'put_value': 0,            # 回售价值
        'call_option_value': 0,    # 转股期权价值
        'revision_value': 0,       # 下修组合期权价值
        'redemption_loss': 0,      # 强赎损失
        'total_value': 0,          # 总估值
        'current_price': 0,        # 当前价格
        'value_deviation': 0,      # 估值偏离度
    }
    
    # 获取基础数据
    price = row.get('price', 100)
    stock_price = row.get('stock_price', 0)
    convert_price = row.get('convert_price', 0)
    years_to_maturity = row.get('years_to_maturity', 3)
    rating = row.get('rating', 'AA')
    premium_rate = row.get('premium_rate', 0)
    
    result['current_price'] = price
    
    # 数据校验
    if pd.isna(stock_price) or stock_price <= 0:
        stock_price = convert_price * 0.8 if convert_price > 0 else 10
    if pd.isna(convert_price) or convert_price <= 0:
        return result
    if pd.isna(years_to_maturity) or years_to_maturity <= 0:
        years_to_maturity = 0.1
    
    # 参数设置
    r = config['risk_free_rate']
    credit_spread = get_credit_spread(rating)
    discount_rate = r + credit_spread
    sigma = config['default_volatility'] * config['volatility_adjustment']
    
    # 回售期估算（一般是最后2年）
    years_to_put = max(0, years_to_maturity - 2)
    
    # 1. 计算债底
    # 计算各期转股概率
    conversion_probs = []
    for year in range(1, int(years_to_maturity) + 2):
        t = min(year, years_to_maturity)
        prob = calculate_conversion_probability(
            stock_price, convert_price, t, sigma,
            config['conversion_threshold']
        )
        conversion_probs.append(prob)
    
    bond_floor = calculate_bond_floor(
        face_value=100,
        coupon_rates=None,  # 使用默认票息
        years_to_maturity=years_to_maturity,
        discount_rate=discount_rate,
        conversion_probs=conversion_probs
    )
    result['bond_floor'] = bond_floor
    
    # 2. 计算回售价值
    put_value = calculate_put_value(
        face_value=100,
        put_price=103,  # 典型回售价格
        years_to_put=years_to_put,
        discount_rate=discount_rate,
        put_probability=0.1  # 历史触发概率约10%
    )
    result['put_value'] = put_value
    
    # 3. 计算转股期权价值
    call_option = calculate_call_option_value(
        S=stock_price,
        K=convert_price,
        T=years_to_maturity,
        sigma=sigma,
        r=r
    )
    result['call_option_value'] = call_option
    
    # 4. 计算下修组合期权价值
    revision_value = calculate_downward_revision_value(
        S=stock_price,
        K=convert_price,
        T=years_to_maturity,
        sigma=sigma,
        r=r,
        years_to_put=years_to_put
    )
    result['revision_value'] = revision_value
    
    # 5. 计算强赎损失
    redemption_loss = calculate_forced_redemption_loss(
        S=stock_price,
        K=convert_price,
        T=years_to_maturity,
        sigma=sigma,
        r=r
    )
    result['redemption_loss'] = redemption_loss
    
    # 总估值 = max(债底, 回售价值) + 期权价值 + 下修价值 - 强赎损失
    base_value = max(bond_floor, bond_floor + put_value)
    total_value = base_value + call_option + revision_value - redemption_loss
    
    result['total_value'] = total_value
    
    # 估值偏离度 = (当前价格 - 估值) / 估值 * 100%
    if total_value > 0:
        result['value_deviation'] = ((price - total_value) / total_value) * 100
    
    return result


def strategy_shengtang(df: pd.DataFrame, top_n: int = 30, 
                       max_premium_rate: float = 50.0) -> pd.DataFrame:
    """
    盛唐策略主函数
    
    计算所有转债的盛唐估值，并按低估程度排序
    
    Args:
        df: 转债数据DataFrame
        top_n: 返回前N只
        max_premium_rate: 最大溢价率筛选条件（默认50%）
        
    Returns:
        排序后的DataFrame
    """
    print("\n" + "=" * 60)
    print("  盛唐策略 - ShengTang Valuation Strategy")
    print("=" * 60)
    print("计算中，请稍候...")
    
    df = df.copy()
    
    # 计算每只转债的盛唐估值
    valuation_results = []
    
    for idx, row in df.iterrows():
        result = calculate_shengtang_value(row)
        valuation_results.append(result)
    
    # 将估值结果合并到DataFrame
    valuation_df = pd.DataFrame(valuation_results)
    
    for col in valuation_df.columns:
        df[f'st_{col}'] = valuation_df[col].values
    
    # 过滤无效数据
    df = df[df['st_total_value'] > 0]
    
    # 只保留低估的（偏离度<0）
    df = df[df['st_value_deviation'] < 0]
    
    # 溢价率筛选
    if 'premium_rate' in df.columns:
        df = df[df['premium_rate'] < max_premium_rate]
        print(f"  溢价率 < {max_premium_rate}% 筛选后: {len(df)} 只")
    
    # 按估值偏离度排序（越低越好，负值表示低估）
    df = df.sort_values('st_value_deviation', ascending=True)
    
    print(f"✓ 盛唐估值计算完成，低估且溢价率<{max_premium_rate}%: {len(df)} 只")
    
    avg_deviation = df['st_value_deviation'].mean() if len(df) > 0 else 0
    print(f"  平均偏离度: {avg_deviation:.2f}%")
    
    return df.head(top_n)


def format_shengtang_output(df: pd.DataFrame) -> pd.DataFrame:
    """
    格式化盛唐策略输出
    """
    display_cols = [
        'cb_code', 'cb_name', 'price', 
        'st_total_value', 'st_value_deviation',
        'st_bond_floor', 'st_call_option_value',
        'st_revision_value', 'st_redemption_loss',
        'premium_rate', 'years_to_maturity', 'stock_name'
    ]
    
    # 重命名列以便显示
    rename_map = {
        'st_total_value': '盛唐估值',
        'st_value_deviation': '偏离度%',
        'st_bond_floor': '债底',
        'st_call_option_value': '期权价值',
        'st_revision_value': '下修价值',
        'st_redemption_loss': '强赎损失',
    }
    
    existing_cols = [col for col in display_cols if col in df.columns]
    result = df[existing_cols].copy()
    
    # 格式化数值
    for col in result.columns:
        if col.startswith('st_') or col in ['price', 'premium_rate', 'years_to_maturity']:
            if col in result.columns:
                result[col] = result[col].round(2)
    
    result = result.rename(columns=rename_map)
    
    return result


# ============ 简化版双低+YTM策略（盛唐文中提到的基础方法）============

def strategy_double_low_ytm(df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    """
    双低+YTM策略（盛唐文中提到的简单方法）
    
    选择低价、低溢价率、高YTM的转债
    """
    df = df.copy()
    
    # 计算双低值
    if 'double_low' not in df.columns:
        df['double_low'] = df['price'] + df['premium_rate']
    
    # 计算简化YTM
    if 'ytm' not in df.columns and 'years_to_maturity' in df.columns:
        df['ytm'] = df.apply(
            lambda x: ((100 - x['price']) / x['price'] / max(x['years_to_maturity'], 0.1)) * 100
            if pd.notna(x['years_to_maturity']) and x['years_to_maturity'] > 0 else 0,
            axis=1
        )
    
    # 综合评分：双低越低越好，YTM越高越好
    df['dl_ytm_score'] = (
        (1 - df['double_low'].rank(pct=True)) * 50 +  # 双低排名
        df['ytm'].rank(pct=True) * 30 +                # YTM排名
        (1 - df['price'].rank(pct=True)) * 20          # 价格排名
    )
    
    df = df.sort_values('dl_ytm_score', ascending=False)
    
    return df.head(top_n)


if __name__ == "__main__":
    # 测试盛唐策略
    from data_fetcher import get_cb_data
    from calculator import calculate_all_indicators
    
    df, msg = get_cb_data()
    if df is not None:
        df = calculate_all_indicators(df)
        
        # 运行盛唐策略
        result = strategy_shengtang(df, top_n=15)
        
        print("\n" + "=" * 60)
        print("  盛唐策略选债结果（按低估程度排序）")
        print("=" * 60)
        print(format_shengtang_output(result))
