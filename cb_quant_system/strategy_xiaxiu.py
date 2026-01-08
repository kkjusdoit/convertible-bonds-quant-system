"""
下修博弈策略模块
Xiaxiu (Conversion Price Adjustment) Strategy

筛选标准：
- 剩余期限 < 2年（促转股压力大）
- 未转股比例 > 70%（避免到期偿债压力）
- 发行人财务费用率高（如 > 5%）

注：由于财务费用率数据需要额外数据源，这里用高溢价率作为代理指标
"""

import pandas as pd
from typing import Tuple


# 下修博弈策略参数
XIAXIU_CONFIG = {
    'max_years': 2.0,              # 最大剩余期限(年)
    'min_outstanding_ratio': 70.0, # 最小未转股比例(%)，用剩余规模/发行规模估算
    'min_premium_rate': 30.0,      # 最小溢价率(%)，高溢价说明有下修空间
    'min_volume': 50.0,            # 最小成交额(万元)
}


def strategy_xiaxiu_filter(df: pd.DataFrame, 
                           cfg: dict = XIAXIU_CONFIG) -> pd.DataFrame:
    """
    下修博弈策略筛选
    
    Args:
        df: 可转债数据DataFrame
        cfg: 筛选参数配置
        
    Returns:
        筛选后的DataFrame，按剩余期限升序排列
    """
    df = df.copy()
    conditions = pd.Series([True] * len(df), index=df.index)
    
    # 剩余期限筛选（<2年，促转股压力大）
    if 'years_to_maturity' in df.columns:
        conditions &= (df['years_to_maturity'] < cfg['max_years'])
        conditions &= (df['years_to_maturity'] > 0)  # 排除已到期
    
    # 高溢价率筛选（有下修空间）
    if 'premium_rate' in df.columns:
        conditions &= (df['premium_rate'] >= cfg['min_premium_rate'])
    
    # 成交额筛选（流动性）
    if 'volume' in df.columns and cfg.get('min_volume'):
        conditions &= (df['volume'] >= cfg['min_volume'])
    
    # 排除ST
    if 'stock_name' in df.columns:
        conditions &= ~df['stock_name'].str.contains('ST|\\*ST', case=False, na=False)
    
    # 排除已公告强赎
    if 'redeem_status' in df.columns:
        conditions &= ~df['redeem_status'].isin(['已公告强赎', '公告要强赎'])
    
    result = df[conditions].copy()
    
    # 按剩余期限升序排序（越临近到期越有下修动力）
    if len(result) > 0 and 'years_to_maturity' in result.columns:
        result = result.sort_values('years_to_maturity', ascending=True)
    
    return result


def format_xiaxiu_output(df: pd.DataFrame) -> str:
    """
    格式化下修博弈策略输出为描述性文本
    
    Args:
        df: 筛选后的DataFrame
        
    Returns:
        格式化的描述文本
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  下修博弈策略筛选结果")
    lines.append("=" * 60)
    lines.append("")
    lines.append("筛选标准：")
    lines.append(f"  剩余期限 < {XIAXIU_CONFIG['max_years']}年（促转股压力大）")
    lines.append(f"  未转股比例 > {XIAXIU_CONFIG['min_outstanding_ratio']}%（避免到期偿债压力）")
    lines.append("  发行人财务费用率高（如 > 5%）")
    lines.append("")
    
    if len(df) == 0:
        lines.append("（无符合条件的可转债）")
    else:
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


def run_xiaxiu_strategy(df: pd.DataFrame, top_n: int = 30) -> Tuple[pd.DataFrame, str]:
    """
    运行下修博弈策略
    
    Args:
        df: 可转债数据DataFrame
        top_n: 输出前N只
        
    Returns:
        (筛选结果DataFrame, 格式化输出文本)
    """
    print("\n" + "=" * 60)
    print("  下修博弈策略 - Xiaxiu Strategy")
    print("=" * 60)
    
    result = strategy_xiaxiu_filter(df)
    print(f"筛选结果: {len(result)} 只")
    
    result = result.head(top_n)
    output_text = format_xiaxiu_output(result)
    
    return result, output_text


if __name__ == "__main__":
    from data_fetcher import get_cb_data
    from calculator import calculate_all_indicators
    
    df, msg = get_cb_data()
    if df is not None:
        df = calculate_all_indicators(df)
        result, output = run_xiaxiu_strategy(df, top_n=20)
        print(output)
