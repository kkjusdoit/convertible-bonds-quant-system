"""
高YTM策略模块
High YTM Strategy - 高到期收益率筛选

筛选标准：
- YTM > 3%（高于同期国债收益率）
- 信用评级 ≥ AA（规避违约风险）
- 剩余期限 > 2年（避免短期流动性冲击）
"""

import pandas as pd
from typing import Tuple


# 高YTM策略参数
HIGH_YTM_CONFIG = {
    'min_ytm': 3.0,              # 最小到期收益率(%)
    'min_rating': 'AA',          # 最低信用评级
    'min_years': 2.0,            # 最小剩余期限(年)
    'min_volume': 50.0,          # 最小成交额(万元)
}

# 评级排序（用于比较）
RATING_ORDER = {
    'AAA': 6, 'AA+': 5, 'AA': 4, 'AA-': 3, 'A+': 2, 'A': 1, 'A-': 0
}


def rating_meets_requirement(rating: str, min_rating: str = 'AA') -> bool:
    """
    判断评级是否满足最低要求
    """
    if pd.isna(rating) or rating == '':
        return False
    rating = str(rating).strip().upper()
    min_rating = min_rating.strip().upper()
    return RATING_ORDER.get(rating, -1) >= RATING_ORDER.get(min_rating, 4)


def strategy_high_ytm_filter(df: pd.DataFrame, 
                              cfg: dict = HIGH_YTM_CONFIG) -> pd.DataFrame:
    """
    高YTM策略筛选
    
    Args:
        df: 可转债数据DataFrame
        cfg: 筛选参数配置
        
    Returns:
        筛选后的DataFrame，按YTM降序排列
    """
    df = df.copy()
    conditions = pd.Series([True] * len(df), index=df.index)
    
    # YTM筛选
    if 'ytm' in df.columns:
        conditions &= (df['ytm'] > cfg['min_ytm'])
    else:
        # 如果没有YTM字段，返回空
        return df.head(0)
    
    # 信用评级筛选
    if 'rating' in df.columns:
        conditions &= df['rating'].apply(
            lambda x: rating_meets_requirement(x, cfg['min_rating'])
        )
    
    # 剩余期限筛选
    if 'years_to_maturity' in df.columns:
        conditions &= (df['years_to_maturity'] > cfg['min_years'])
    
    # 成交额筛选（流动性）
    if 'volume' in df.columns and cfg.get('min_volume'):
        conditions &= (df['volume'] >= cfg['min_volume'])
    
    # 排除ST
    if 'stock_name' in df.columns:
        conditions &= ~df['stock_name'].str.contains('ST|\\*ST', case=False, na=False)
    
    result = df[conditions].copy()
    
    # 按YTM降序排序
    if len(result) > 0 and 'ytm' in result.columns:
        result = result.sort_values('ytm', ascending=False)
    
    return result


def format_high_ytm_output(df: pd.DataFrame) -> str:
    """
    格式化高YTM策略输出为描述性文本
    
    Args:
        df: 筛选后的DataFrame
        
    Returns:
        格式化的描述文本
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  高YTM策略筛选结果")
    lines.append("=" * 60)
    lines.append("")
    lines.append("筛选标准：")
    lines.append(f"  YTM > {HIGH_YTM_CONFIG['min_ytm']}%（高于同期国债收益率）")
    lines.append(f"  信用评级 ≥ {HIGH_YTM_CONFIG['min_rating']}（规避违约风险）")
    lines.append(f"  剩余期限 > {HIGH_YTM_CONFIG['min_years']}年（避免短期流动性冲击）")
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
            ytm = row.get('ytm', 0)
            rating = row.get('rating', 'N/A')
            years = row.get('years_to_maturity', 0)
            
            line = (f"{idx}. 转债名称【{cb_name}】，"
                    f"转债价格【{price:.3f}】元，"
                    f"涨跌幅【{change_pct:.2f}%】，"
                    f"转股价值【{convert_value:.2f}】元，"
                    f"溢价率【{premium_rate:.2f}%】，"
                    f"YTM【{ytm:.2f}%】，"
                    f"评级【{rating}】，"
                    f"剩余期限【{years:.2f}年】。")
            lines.append(line)
    
    return "\n".join(lines)


def run_high_ytm_strategy(df: pd.DataFrame, top_n: int = 30) -> Tuple[pd.DataFrame, str]:
    """
    运行高YTM策略
    
    Args:
        df: 可转债数据DataFrame
        top_n: 输出前N只
        
    Returns:
        (筛选结果DataFrame, 格式化输出文本)
    """
    print("\n" + "=" * 60)
    print("  高YTM策略 - High YTM Strategy")
    print("=" * 60)
    
    result = strategy_high_ytm_filter(df)
    print(f"筛选结果: {len(result)} 只")
    
    result = result.head(top_n)
    output_text = format_high_ytm_output(result)
    
    return result, output_text


if __name__ == "__main__":
    from data_fetcher import get_cb_data
    from calculator import calculate_all_indicators
    
    df, msg = get_cb_data()
    if df is not None:
        df = calculate_all_indicators(df)
        result, output = run_high_ytm_strategy(df, top_n=20)
        print(output)
