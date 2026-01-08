"""
盛唐简化估值策略
ShengTang Simple Valuation - 低溢价偏离债池

简化版估值公式：
估值 ≈ max(债底, 转股价值) + 期权时间价值

筛选条件：
- 溢价率 < 10%（低溢价）
- 偏离度 < 0（低估）
- 价格 < 200元（过滤高价妖债）
"""

import pandas as pd
import numpy as np
from typing import Tuple


# 简化估值参数
SIMPLE_CONFIG = {
    'discount_rate': 0.03,       # 折现率
    'max_premium_rate': 10.0,    # 最大溢价率
    'max_price': 200.0,          # 最大价格
    'min_volume': 50.0,          # 最小成交额
}


def simple_valuation(row: pd.Series) -> Tuple[float, float]:
    """
    简化版盛唐估值
    
    Args:
        row: 单只转债数据
        
    Returns:
        (估值, 偏离度)
    """
    price = row.get('price', 100)
    convert_value = row.get('convert_value', 0)
    years = row.get('years_to_maturity', 3)
    
    if pd.isna(convert_value) or convert_value <= 0:
        return None, None
    if pd.isna(years) or years <= 0:
        years = 0.5
    
    # 债底：100/(1+r)^t
    r = SIMPLE_CONFIG['discount_rate']
    bond_floor = 100 / ((1 + r) ** max(years, 0.5))
    
    # 期权价值
    if convert_value >= 100:
        # 实值期权：内在价值 + 时间价值
        option_value = (convert_value - 100) + 5
    else:
        # 虚值期权：时间价值
        option_value = max(0, (100 - convert_value) * 0.3 * min(years, 3))
    
    # 总估值 = max(债底, 转股价值) + 期权价值*0.5
    total_value = max(bond_floor, convert_value) + option_value * 0.5
    
    # 偏离度 = (价格 - 估值) / 估值
    deviation = ((price - total_value) / total_value) * 100
    
    return total_value, deviation


def strategy_shengtang_simple(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    盛唐简化估值策略 - 低溢价偏离债池
    
    Args:
        df: 可转债数据
        top_n: 返回前N只
        
    Returns:
        筛选后的DataFrame
    """
    print("\n" + "=" * 60)
    print("  盛唐简化估值 - 低溢价偏离债池")
    print("=" * 60)
    
    df = df.copy()
    
    # 计算简化估值
    df['simple_value'], df['simple_deviation'] = zip(*df.apply(simple_valuation, axis=1))
    
    # 筛选条件
    conditions = (
        (df['simple_value'].notna()) &
        (df['simple_deviation'] < 0) &  # 低估
        (df['premium_rate'] < SIMPLE_CONFIG['max_premium_rate']) &  # 低溢价
        (df['price'] < SIMPLE_CONFIG['max_price'])  # 过滤高价
    )
    
    if 'volume' in df.columns:
        conditions &= (df['volume'] >= SIMPLE_CONFIG['min_volume'])
    
    result = df[conditions].copy()
    result = result.sort_values('simple_deviation', ascending=True)
    
    print(f"✓ 低溢价偏离债池: {len(result)} 只")
    
    return result.head(top_n)


def format_simple_output(df: pd.DataFrame) -> str:
    """格式化输出"""
    if len(df) == 0:
        return "（无符合条件的可转债）"
    
    lines = []
    for _, row in df.iterrows():
        name = row.get('cb_name', 'N/A').replace('转债', '')
        deviation = row.get('simple_deviation', 0)
        lines.append(f"{name}{deviation:.0f}%")
    
    return "■低溢价偏离债池：" + "，".join(lines)


def run_shengtang_simple(df: pd.DataFrame, top_n: int = 20) -> Tuple[pd.DataFrame, str]:
    """运行策略"""
    result = strategy_shengtang_simple(df, top_n)
    
    # 简洁输出格式（类似盛唐原版）
    short_output = format_simple_output(result)
    
    # 详细输出
    lines = []
    lines.append("=" * 60)
    lines.append("  盛唐简化估值 - 低溢价偏离债池")
    lines.append("=" * 60)
    lines.append("")
    lines.append("**筛选标准：**")
    lines.append(f"- 溢价率 < {SIMPLE_CONFIG['max_premium_rate']}%")
    lines.append(f"- 价格 < {SIMPLE_CONFIG['max_price']}元")
    lines.append("- 偏离度 < 0（低估）")
    lines.append("")
    lines.append(f"**筛选结果（共 {len(result)} 只）：**")
    lines.append("")
    
    for idx, (_, row) in enumerate(result.iterrows(), 1):
        line = (f"{idx}. 转债名称【{row.get('cb_name', 'N/A')}】，"
                f"当前价格【{row.get('price', 0):.3f}】元，"
                f"简化估值【{row.get('simple_value', 0):.2f}】元，"
                f"偏离度【{row.get('simple_deviation', 0):.0f}%】，"
                f"溢价率【{row.get('premium_rate', 0):.2f}%】。")
        lines.append(line)
    
    detail_output = "\n".join(lines)
    
    return result, detail_output


if __name__ == "__main__":
    from data_fetcher import get_cb_data
    from calculator import calculate_all_indicators
    
    df, _ = get_cb_data()
    df = calculate_all_indicators(df)
    
    result, output = run_shengtang_simple(df, top_n=15)
    print(output)
    print("\n" + "=" * 60)
    print(format_simple_output(result))
