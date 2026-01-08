#!/usr/bin/env python3
"""
可转债量化选债系统 - 汇总报告生成
生成包含所有策略结果的Markdown报告
"""

from datetime import datetime
import pandas as pd

from data_fetcher import get_cb_data
from calculator import calculate_all_indicators, calculate_composite_score
from strategy_double_low import strategy_double_low_filter, DOUBLE_LOW_CONFIG
from strategy_high_ytm import strategy_high_ytm_filter, HIGH_YTM_CONFIG
from strategy_xiaxiu import strategy_xiaxiu_filter, XIAXIU_CONFIG
from strategy_kashu2026 import strategy_kashu2026, KASHU_CONFIG
from strategy_shengtang import strategy_shengtang
from strategy_shengtang_simple import strategy_shengtang_simple, format_simple_output, SIMPLE_CONFIG
from strategy import strategy_low_premium, strategy_double_low, strategy_high_ytm, strategy_composite_score


def format_cb_list(df: pd.DataFrame, max_items: int = 20) -> str:
    """格式化可转债列表为描述文本"""
    if len(df) == 0:
        return "（无符合条件的可转债）\n"
    
    lines = []
    for idx, (_, row) in enumerate(df.head(max_items).iterrows(), 1):
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
    
    if len(df) > max_items:
        lines.append(f"\n... 共 {len(df)} 只，仅显示前 {max_items} 只")
    
    return "\n".join(lines)


def generate_report(top_n: int = 20) -> str:
    """生成汇总报告"""
    
    # 获取数据
    print("正在获取数据...")
    df, msg = get_cb_data()
    if df is None:
        return f"# 错误\n\n{msg}"
    
    # 计算指标
    print("正在计算指标...")
    df = calculate_all_indicators(df)
    df = calculate_composite_score(df)
    
    # 生成报告
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report = []
    report.append(f"# 可转债量化选债报告")
    report.append(f"\n生成时间：{now}")
    report.append(f"\n全市场可转债数量：{len(df)} 只")
    report.append("")
    
    # 市场概览
    report.append("## 市场概览")
    report.append("")
    report.append(f"- 平均价格：{df['price'].mean():.2f} 元")
    report.append(f"- 价格中位数：{df['price'].median():.2f} 元")
    report.append(f"- 平均溢价率：{df['premium_rate'].mean():.2f}%")
    report.append(f"- 溢价率中位数：{df['premium_rate'].median():.2f}%")
    if 'double_low' in df.columns:
        report.append(f"- 平均双低值：{df['double_low'].mean():.2f}")
    report.append("")
    
    # 策略一：双低策略
    report.append("---")
    report.append("")
    report.append("## 一、双低策略")
    report.append("")
    report.append("**筛选标准：**")
    report.append(f"- 价格区间：{DOUBLE_LOW_CONFIG['min_price']}-{DOUBLE_LOW_CONFIG['max_price']}元（避免高价股性风险）")
    report.append(f"- 转股溢价率：<{DOUBLE_LOW_CONFIG['max_premium_rate']}%（确保股性跟随能力）")
    report.append(f"- 剩余规模：<{DOUBLE_LOW_CONFIG['max_outstanding']}亿元（提升资金关注度）")
    report.append("")
    
    print("正在执行双低策略...")
    double_low_result = strategy_double_low_filter(df)
    report.append(f"**筛选结果（共 {len(double_low_result)} 只）：**")
    report.append("")
    report.append(format_cb_list(double_low_result, top_n))
    report.append("")
    
    # 策略二：高YTM策略
    report.append("---")
    report.append("")
    report.append("## 二、高YTM策略")
    report.append("")
    report.append("**筛选标准：**")
    report.append(f"- YTM > {HIGH_YTM_CONFIG['min_ytm']}%（高于同期国债收益率）")
    report.append(f"- 信用评级 ≥ {HIGH_YTM_CONFIG['min_rating']}（规避违约风险）")
    report.append(f"- 剩余期限 > {HIGH_YTM_CONFIG['min_years']}年（避免短期流动性冲击）")
    report.append("")
    
    print("正在执行高YTM策略...")
    high_ytm_result = strategy_high_ytm_filter(df)
    report.append(f"**筛选结果（共 {len(high_ytm_result)} 只）：**")
    report.append("")
    report.append(format_cb_list(high_ytm_result, top_n))
    report.append("")
    
    # 策略三：下修博弈策略
    report.append("---")
    report.append("")
    report.append("## 三、下修博弈策略")
    report.append("")
    report.append("**筛选标准：**")
    report.append(f"- 剩余期限 < {XIAXIU_CONFIG['max_years']}年（促转股压力大）")
    report.append(f"- 未转股比例 > {XIAXIU_CONFIG['min_outstanding_ratio']}%（避免到期偿债压力）")
    report.append("- 发行人财务费用率高（如 > 5%）")
    report.append("")
    
    print("正在执行下修博弈策略...")
    xiaxiu_result = strategy_xiaxiu_filter(df)
    report.append(f"**筛选结果（共 {len(xiaxiu_result)} 只）：**")
    report.append("")
    report.append(format_cb_list(xiaxiu_result, top_n))
    report.append("")
    
    # 策略四：卡叔2026策略
    report.append("---")
    report.append("")
    report.append("## 四、卡叔2026策略")
    report.append("")
    report.append("**策略说明：** 四大类转债筛选")
    report.append("")
    
    print("正在执行卡叔2026策略...")
    kashu_results = strategy_kashu2026(df, top_n)
    
    # 4.1 小市值高溢价
    report.append("### 4.1 小市值高溢价（博弈下修）")
    report.append("")
    report.append("**筛选标准：**")
    report.append(f"- 剩余规模 ≤ {KASHU_CONFIG['type1']['max_outstanding']}亿元")
    report.append(f"- 溢价率 ≥ {KASHU_CONFIG['type1']['min_premium_rate']}%")
    report.append(f"- 价格区间：{KASHU_CONFIG['type1']['min_price']}-{KASHU_CONFIG['type1']['max_price']}元")
    report.append("")
    type1_df = kashu_results.get('type1_小市值高溢价', pd.DataFrame())
    report.append(f"**筛选结果（共 {len(type1_df)} 只）：**")
    report.append("")
    report.append(format_cb_list(type1_df, top_n))
    report.append("")
    
    # 4.2 防御临期债
    report.append("### 4.2 绝对防御临期债")
    report.append("")
    report.append("**筛选标准：**")
    report.append(f"- 剩余年限 ≤ {KASHU_CONFIG['type2']['max_years']}年")
    report.append(f"- 价格 ≤ {KASHU_CONFIG['type2']['max_price']}元")
    report.append(f"- 溢价率 ≤ {KASHU_CONFIG['type2']['max_premium_rate']}%")
    report.append("")
    type2_df = kashu_results.get('type2_防御临期债', pd.DataFrame())
    report.append(f"**筛选结果（共 {len(type2_df)} 只）：**")
    report.append("")
    report.append(format_cb_list(type2_df, top_n))
    report.append("")
    
    # 4.3 大股东未减持
    report.append("### 4.3 大股东未减持")
    report.append("")
    report.append("**筛选标准：**")
    report.append(f"- 剩余规模 ≥ {KASHU_CONFIG['type3']['min_outstanding']}亿元")
    report.append(f"- 剩余年限：{KASHU_CONFIG['type3']['min_years']}-{KASHU_CONFIG['type3']['max_years']}年")
    report.append("")
    type3_df = kashu_results.get('type3_大股东未减持', pd.DataFrame())
    report.append(f"**筛选结果（共 {len(type3_df)} 只）：**")
    report.append("")
    report.append(format_cb_list(type3_df, top_n))
    report.append("")
    
    # 4.4 两年期
    report.append("### 4.4 存续期2年附近")
    report.append("")
    report.append("**筛选标准：**")
    report.append(f"- 剩余年限：{KASHU_CONFIG['type4']['min_years']}-{KASHU_CONFIG['type4']['max_years']}年")
    report.append(f"- 价格 ≤ {KASHU_CONFIG['type4']['max_price']}元")
    report.append("")
    type4_df = kashu_results.get('type4_两年期', pd.DataFrame())
    report.append(f"**筛选结果（共 {len(type4_df)} 只）：**")
    report.append("")
    report.append(format_cb_list(type4_df, top_n))
    report.append("")
    
    # 策略五：盛唐估值策略
    report.append("---")
    report.append("")
    report.append("## 五、盛唐估值策略（专业版）")
    report.append("")
    report.append("**策略说明：** 基于BS模型的专业估值")
    report.append("")
    report.append("核心公式：转债估值 = max(债底,回售价值) + 转股期权价值 + 下修期权价值 - 强赎损失")
    report.append("")
    
    print("正在执行盛唐估值策略...")
    shengtang_result = strategy_shengtang(df, top_n)
    report.append(f"**筛选结果（按低估程度排序，共 {len(shengtang_result)} 只）：**")
    report.append("")
    report.append(format_shengtang_list(shengtang_result, top_n))
    report.append("")
    
    # 策略5.5：盛唐简化版 - 低溢价偏离债池
    report.append("---")
    report.append("")
    report.append("## 五-2、盛唐简化版（低溢价偏离债池）")
    report.append("")
    report.append("**策略说明：** 简化估值，筛选低溢价+低估转债")
    report.append("")
    report.append("**筛选标准：**")
    report.append(f"- 溢价率 < {SIMPLE_CONFIG['max_premium_rate']}%")
    report.append(f"- 价格 < {SIMPLE_CONFIG['max_price']}元")
    report.append("- 偏离度 < 0（低估）")
    report.append("")
    
    print("正在执行盛唐简化版...")
    simple_result = strategy_shengtang_simple(df, top_n)
    report.append(f"**筛选结果（共 {len(simple_result)} 只）：**")
    report.append("")
    report.append(format_simple_output(simple_result))
    report.append("")
    report.append(format_simple_list(simple_result, top_n))
    report.append("")
    
    # 策略六：综合评分策略
    report.append("---")
    report.append("")
    report.append("## 六、综合评分策略")
    report.append("")
    report.append("**策略说明：** 多因子均衡选债")
    report.append("")
    
    print("正在执行综合评分策略...")
    composite_result = strategy_composite_score(df, top_n)
    report.append(f"**筛选结果（共 {len(composite_result)} 只）：**")
    report.append("")
    report.append(format_cb_list(composite_result, top_n))
    report.append("")
    
    # 策略七：低溢价策略
    report.append("---")
    report.append("")
    report.append("## 七、低溢价策略")
    report.append("")
    report.append("**策略说明：** 选择溢价率最低的转债，适合看好正股上涨")
    report.append("")
    
    print("正在执行低溢价策略...")
    low_premium_result = strategy_low_premium(df, top_n)
    report.append(f"**筛选结果（共 {len(low_premium_result)} 只）：**")
    report.append("")
    report.append(format_cb_list(low_premium_result, top_n))
    report.append("")
    
    # 免责声明
    report.append("---")
    report.append("")
    report.append("## 免责声明")
    report.append("")
    report.append("以上结果仅供参考，不构成投资建议。建议结合正股基本面和市场环境综合判断。")
    report.append("")
    
    return "\n".join(report)


def format_shengtang_list(df: pd.DataFrame, max_items: int = 20) -> str:
    """格式化盛唐策略输出"""
    if len(df) == 0:
        return "（无符合条件的可转债）\n"
    
    lines = []
    for idx, (_, row) in enumerate(df.head(max_items).iterrows(), 1):
        cb_name = row.get('cb_name', 'N/A')
        price = row.get('price', 0)
        total_value = row.get('st_total_value', 0)
        deviation = row.get('st_value_deviation', 0)
        premium_rate = row.get('premium_rate', 0)
        
        line = (f"{idx}. 转债名称【{cb_name}】，"
                f"当前价格【{price:.3f}】元，"
                f"盛唐估值【{total_value:.2f}】元，"
                f"偏离度【{deviation:.2f}%】，"
                f"溢价率【{premium_rate:.2f}%】。")
        lines.append(line)
    
    if len(df) > max_items:
        lines.append(f"\n... 共 {len(df)} 只，仅显示前 {max_items} 只")
    
    return "\n".join(lines)


def format_simple_list(df: pd.DataFrame, max_items: int = 20) -> str:
    """格式化简化版盛唐输出"""
    if len(df) == 0:
        return "（无符合条件的可转债）\n"
    
    lines = []
    for idx, (_, row) in enumerate(df.head(max_items).iterrows(), 1):
        cb_name = row.get('cb_name', 'N/A')
        price = row.get('price', 0)
        simple_value = row.get('simple_value', 0)
        deviation = row.get('simple_deviation', 0)
        premium_rate = row.get('premium_rate', 0)
        
        line = (f"{idx}. 转债名称【{cb_name}】，"
                f"当前价格【{price:.3f}】元，"
                f"简化估值【{simple_value:.2f}】元，"
                f"偏离度【{deviation:.0f}%】，"
                f"溢价率【{premium_rate:.2f}%】。")
        lines.append(line)
    
    if len(df) > max_items:
        lines.append(f"\n... 共 {len(df)} 只，仅显示前 {max_items} 只")
    
    return "\n".join(lines)


def main():
    """主函数"""
    print("=" * 60)
    print("  可转债量化选债系统 - 汇总报告生成")
    print("=" * 60)
    
    report = generate_report(top_n=20)
    
    # 保存报告
    filename = f"cb_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✓ 报告已生成: {filename}")
    print("\n" + "=" * 60)
    print(report)


if __name__ == "__main__":
    main()
