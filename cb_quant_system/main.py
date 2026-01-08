#!/usr/bin/env python3
"""
可转债量化选债系统 - 主程序
Convertible Bond Quantitative Selection System - Main Entry

功能：
1. 获取全市场可转债数据
2. 计算关键量化指标
3. 实施多种选债策略
4. 输出筛选结果

使用方法：
    python main.py
    python main.py --output result.csv
    python main.py --max-premium 30 --min-ytm -5 --top 20

作者：Quantitative Developer
日期：2024
"""

import argparse
import sys
from datetime import datetime
import pandas as pd

# 导入自定义模块
from data_fetcher import get_cb_data
from calculator import calculate_all_indicators, calculate_composite_score
from strategy import (
    filter_by_basic_criteria,
    filter_by_risk,
    run_all_strategies,
    format_output,
    strategy_composite_score
)
from strategy_kashu2026 import strategy_kashu2026, format_kashu_output
from strategy_shengtang import strategy_shengtang, format_shengtang_output
from strategy_double_low import run_double_low_strategy
from strategy_high_ytm import run_high_ytm_strategy
from strategy_xiaxiu import run_xiaxiu_strategy
import config


def parse_arguments():
    """
    解析命令行参数
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(
        description='可转债量化选债系统 - Convertible Bond Quantitative Selection System'
    )
    
    parser.add_argument(
        '--max-premium', 
        type=float, 
        default=config.MAX_PREMIUM_RATE,
        help=f'最大转股溢价率(%%)，默认{config.MAX_PREMIUM_RATE}'
    )
    
    parser.add_argument(
        '--min-ytm', 
        type=float, 
        default=config.MIN_YTM,
        help=f'最小到期收益率(%%)，默认{config.MIN_YTM}'
    )
    
    parser.add_argument(
        '--min-volume', 
        type=float, 
        default=config.MIN_DAILY_VOLUME,
        help=f'最小成交额(万元)，默认{config.MIN_DAILY_VOLUME}'
    )
    
    parser.add_argument(
        '--max-price', 
        type=float, 
        default=config.MAX_PRICE,
        help=f'最大价格，默认{config.MAX_PRICE}'
    )
    
    parser.add_argument(
        '--min-price', 
        type=float, 
        default=config.MIN_PRICE,
        help=f'最小价格，默认{config.MIN_PRICE}'
    )
    
    parser.add_argument(
        '--top', 
        type=int, 
        default=config.TOP_N,
        help=f'输出前N只债券，默认{config.TOP_N}'
    )
    
    parser.add_argument(
        '--output', 
        type=str, 
        default=config.DEFAULT_OUTPUT_FILE,
        help=f'输出CSV文件名，默认{config.DEFAULT_OUTPUT_FILE}'
    )
    
    parser.add_argument(
        '--strategy',
        type=str,
        choices=['all', 'composite', 'low_premium', 'double_low', 'high_ytm', 'value', 'kashu2026', 'shengtang', 'double_low_filter', 'high_ytm_filter', 'xiaxiu'],
        default='composite',
        help='选债策略，默认composite(综合评分)，xiaxiu为下修博弈策略'
    )
    
    parser.add_argument(
        '--no-filter',
        action='store_true',
        help='不进行基础筛选，显示全部数据'
    )
    
    return parser.parse_args()


def print_header():
    """打印程序头部信息"""
    print("\n" + "=" * 60)
    print("  可转债量化选债系统 v1.0")
    print("  Convertible Bond Quantitative Selection System")
    print("=" * 60)
    print(f"  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")


def print_market_overview(df: pd.DataFrame):
    """
    打印市场概览
    Print market overview statistics
    """
    print("\n" + "-" * 40)
    print("市场概览 Market Overview")
    print("-" * 40)
    
    print(f"可转债总数: {len(df)} 只")
    
    if 'price' in df.columns:
        print(f"平均价格: {df['price'].mean():.2f} 元")
        print(f"价格中位数: {df['price'].median():.2f} 元")
        print(f"价格范围: {df['price'].min():.2f} - {df['price'].max():.2f} 元")
    
    if 'premium_rate' in df.columns:
        print(f"平均溢价率: {df['premium_rate'].mean():.2f}%")
        print(f"溢价率中位数: {df['premium_rate'].median():.2f}%")
    
    if 'ytm' in df.columns:
        valid_ytm = df['ytm'].dropna()
        if len(valid_ytm) > 0:
            print(f"平均YTM: {valid_ytm.mean():.2f}%")
    
    if 'double_low' in df.columns:
        print(f"平均双低值: {df['double_low'].mean():.2f}")
        print(f"双低值中位数: {df['double_low'].median():.2f}")
    
    print("-" * 40 + "\n")


def print_results(df: pd.DataFrame, strategy_name: str):
    """
    打印选债结果
    Print selection results
    """
    print("\n" + "=" * 60)
    print(f"  {strategy_name} 选债结果")
    print("=" * 60)
    
    # 格式化输出
    output_df = format_output(df)
    
    # 设置pandas显示选项
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 20)
    
    print(output_df.to_string(index=False))
    print("\n" + "=" * 60)


def save_results(df: pd.DataFrame, filename: str):
    """
    保存结果到CSV文件
    Save results to CSV file
    """
    try:
        output_df = format_output(df)
        output_df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✓ 结果已保存到: {filename}")
    except Exception as e:
        print(f"\n✗ 保存文件失败: {e}")


def main():
    """主函数"""
    # 打印头部
    print_header()
    
    # 解析参数
    args = parse_arguments()
    
    print("参数设置:")
    print(f"  最大溢价率: {args.max_premium}%")
    print(f"  最小YTM: {args.min_ytm}%")
    print(f"  最小成交额: {args.min_volume}万元")
    print(f"  价格范围: {args.min_price}-{args.max_price}元")
    print(f"  输出数量: {args.top}只")
    print(f"  选债策略: {args.strategy}")
    
    # Step 1: 获取数据
    print("\n" + "=" * 50)
    print("Step 1: 获取可转债数据")
    print("=" * 50)
    
    df, msg = get_cb_data()
    
    if df is None:
        print(f"\n✗ 错误: {msg}")
        print("请检查网络连接或稍后重试")
        sys.exit(1)
    
    # Step 2: 计算指标
    print("\n" + "=" * 50)
    print("Step 2: 计算量化指标")
    print("=" * 50)
    
    df = calculate_all_indicators(df)
    df = calculate_composite_score(df)
    
    # 打印市场概览
    print_market_overview(df)
    
    # Step 3: 筛选过滤
    if not args.no_filter:
        print("\n" + "=" * 50)
        print("Step 3: 基础筛选与风险过滤")
        print("=" * 50)
        
        df = filter_by_basic_criteria(
            df,
            max_premium=args.max_premium,
            min_ytm=args.min_ytm,
            min_volume=args.min_volume,
            max_price=args.max_price,
            min_price=args.min_price
        )
        
        df = filter_by_risk(df)
        
        if len(df) == 0:
            print("\n✗ 筛选后无符合条件的转债，请调整筛选参数")
            sys.exit(1)
    
    # Step 4: 运行策略
    print("\n" + "=" * 50)
    print("Step 4: 运行选债策略")
    print("=" * 50)
    
    # 卡叔2026策略
    if args.strategy == 'kashu2026':
        results = strategy_kashu2026(df, args.top)
        
        for strategy_name, result_df in results.items():
            if len(result_df) > 0:
                print(f"\n{'='*60}")
                print(f"  {strategy_name}")
                print('='*60)
                output_df = format_kashu_output(result_df, strategy_name)
                pd.set_option('display.max_columns', None)
                pd.set_option('display.width', None)
                print(output_df.to_string(index=False))
        
        # 保存综合评分榜
        if '综合评分榜' in results:
            save_results(results['综合评分榜'], args.output)
    
    # 双低筛选策略
    elif args.strategy == 'double_low_filter':
        result_df, output_text = run_double_low_strategy(df, args.top)
        print(output_text)
        
        # 保存结果
        result_df.to_csv(args.output, index=False, encoding='utf-8-sig')
        print(f"\n✓ 结果已保存到: {args.output}")
    
    # 高YTM筛选策略
    elif args.strategy == 'high_ytm_filter':
        result_df, output_text = run_high_ytm_strategy(df, args.top)
        print(output_text)
        
        # 保存结果
        if len(result_df) > 0:
            result_df.to_csv(args.output, index=False, encoding='utf-8-sig')
            print(f"\n✓ 结果已保存到: {args.output}")
    
    # 下修博弈策略
    elif args.strategy == 'xiaxiu':
        result_df, output_text = run_xiaxiu_strategy(df, args.top)
        print(output_text)
        
        # 保存结果
        if len(result_df) > 0:
            result_df.to_csv(args.output, index=False, encoding='utf-8-sig')
            print(f"\n✓ 结果已保存到: {args.output}")
    
    # 盛唐策略
    elif args.strategy == 'shengtang':
        result_df = strategy_shengtang(df, args.top)
        
        print(f"\n{'='*60}")
        print("  盛唐策略选债结果（按低估程度排序）")
        print('='*60)
        output_df = format_shengtang_output(result_df)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(output_df.to_string(index=False))
        
        # 保存结果
        result_df.to_csv(args.output, index=False, encoding='utf-8-sig')
        print(f"\n✓ 结果已保存到: {args.output}")
    
    elif args.strategy == 'all':
        # 运行所有策略
        results = run_all_strategies(df, args.top)
        
        for strategy_name, result_df in results.items():
            if len(result_df) > 0:
                print_results(result_df, strategy_name)
        
        # 保存综合评分策略结果
        if '综合评分策略' in results:
            save_results(results['综合评分策略'], args.output)
    else:
        # 运行单一策略
        strategy_map = {
            'composite': ('综合评分策略', strategy_composite_score),
            'low_premium': ('低溢价策略', lambda d, n: d.nsmallest(n, 'premium_rate')),
            'double_low': ('双低策略', lambda d, n: d.nsmallest(n, 'double_low')),
            'high_ytm': ('高YTM策略', lambda d, n: d.nlargest(n, 'ytm')),
            'value': ('价值挖掘策略', lambda d, n: d[(d['price'] < 105) & (d['premium_rate'] < 15)].nsmallest(n, 'double_low'))
        }
        
        strategy_name, strategy_func = strategy_map[args.strategy]
        result_df = strategy_func(df, args.top)
        
        print_results(result_df, strategy_name)
        save_results(result_df, args.output)
    
    # 完成
    print("\n" + "=" * 60)
    print("  选债完成！")
    print("=" * 60)
    print("\n提示:")
    print("- 以上结果仅供参考，不构成投资建议")
    print("- 建议结合正股基本面和市场环境综合判断")
    print("- 可通过调整config.py中的参数优化策略")
    print("\n")


if __name__ == "__main__":
    main()
