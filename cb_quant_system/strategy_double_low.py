"""
双低策略模块
Double Low Strategy - 价格+溢价率双低筛选

筛选标准：
- 价格区间：100-120元（避免高价股性风险）
- 转股溢价率：<20%（确保股性跟随能力）
- 剩余规模：<15亿元（提升资金关注度）
"""

import pandas as pd
from typing import Tuple


# 双低策略参数
DOUBLE_LOW_CONFIG = {
    'min_price': 100.0,          # 最小价格
    'max_price': 120.0,          # 最大价格
    'max_premium_rate': 20.0,    # 最大转股溢价率(%)
    'max_outstanding': 15.0,     # 最大剩余规模(亿元)
    'min_volume': 50.0,          # 最小成交额(万元)
}


def strategy_double_low_filter(df: pd.DataFrame, 
                                cfg: dict = DOUBLE_LOW_CONFIG) -> pd.DataFrame:
    """
    双低策略筛选
    
    Args:
        df: 可转债数据DataFrame
        cfg: 筛选参数配置
        
    Returns:
        筛选后的DataFrame，按双低值升序排列
    """
    df = df.copy()
    conditions = pd.Series([True] * len(df), index=df.index)
    
    # 价格区间筛选
    if 'price' in df.columns:
        conditions &= (df['price'] >= cfg['min_price'])
        conditions &= (df['price'] <= cfg['max_price'])
    
    # 转股溢价率筛选
    if 'premium_rate' in df.columns:
        conditions &= (df['premium_rate'] < cfg['max_premium_rate'])
    
    # 剩余规模筛选
    if 'outstanding' in df.columns:
        conditions &= (df['outstanding'] < cfg['max_outstanding'])
    
    # 成交额筛选（流动性）
    if 'volume' in df.columns and cfg.get('min_volume'):
        conditions &= (df['volume'] >= cfg['min_volume'])
    
    # 排除ST
    if 'stock_name' in df.columns:
        conditions &= ~df['stock_name'].str.contains('ST|\\*ST', case=False, na=False)
    
    result = df[conditions].copy()
    
    # 计算双低值并排序
    if len(result) > 0 and 'price' in result.columns and 'premium_rate' in result.columns:
        result['double_low'] = result['price'] + result['premium_rate']
        result = result.sort_values('double_low', ascending=True)
    
    return result


def format_double_low_output(df: pd.DataFrame) -> str:
    """
    格式化双低策略输出为描述性文本
    
    Args:
        df: 筛选后的DataFrame
        
    Returns:
        格式化的描述文本
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  双低策略筛选结果")
    lines.append("=" * 60)
    lines.append("")
    lines.append("筛选标准：")
    lines.append(f"  价格区间：{DOUBLE_LOW_CONFIG['min_price']}-{DOUBLE_LOW_CONFIG['max_price']}元（避免高价股性风险）")
    lines.append(f"  转股溢价率：<{DOUBLE_LOW_CONFIG['max_premium_rate']}%（确保股性跟随能力）")
    lines.append(f"  剩余规模：<{DOUBLE_LOW_CONFIG['max_outstanding']}亿元（提升资金关注度）")
    lines.append("")
    lines.append(f"符合筛选条件的可转债共 {len(df)} 只：")
    lines.append("-" * 60)
    
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        cb_name = row.get('cb_name', 'N/A')
        price = row.get('price', 0)
        change_pct = row.get('change_pct', 0)
        convert_value = row.get('convert_value', 0)
        premium_rate = row.get('premium_rate', 0)
        turnover_rate = row.get('turnover_rate', 0)
        
        line = (f"{idx}. 转债名称【{cb_name}】，"
                f"转债价格【{price:.3f}】元，"
                f"涨跌幅【{change_pct:.2f}%】，"
                f"转股价值【{convert_value:.2f}】元，"
                f"溢价率【{premium_rate:.2f}%】，"
                f"换手率【{turnover_rate:.2f}%】。")
        lines.append(line)
    
    return "\n".join(lines)


def run_double_low_strategy(df: pd.DataFrame, top_n: int = 30) -> Tuple[pd.DataFrame, str]:
    """
    运行双低策略
    
    Args:
        df: 可转债数据DataFrame
        top_n: 输出前N只
        
    Returns:
        (筛选结果DataFrame, 格式化输出文本)
    """
    print("\n" + "=" * 60)
    print("  双低策略 - Double Low Strategy")
    print("=" * 60)
    
    result = strategy_double_low_filter(df)
    print(f"筛选结果: {len(result)} 只")
    
    result = result.head(top_n)
    output_text = format_double_low_output(result)
    
    return result, output_text


if __name__ == "__main__":
    from data_fetcher import get_cb_data
    from calculator import calculate_all_indicators
    
    df, msg = get_cb_data()
    if df is not None:
        df = calculate_all_indicators(df)
        result, output = run_double_low_strategy(df, top_n=20)
        print(output)
