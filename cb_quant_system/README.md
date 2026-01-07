# 可转债量化选债系统 (Convertible Bond Quantitative Selection System)

## 简介
本系统用于中国可转债市场的量化选债，通过获取实时数据、计算关键指标、实施筛选策略来辅助投资决策。

## 功能特点
- 获取全市场可转债实时数据（使用Akshare免费数据源）
- 计算关键量化指标：转股溢价率、到期收益率、转股价值、纯债价值等
- 多因子综合评分选债策略
- 风险过滤和流动性筛选
- 结果导出为CSV文件

## 环境要求
- Python 3.8+
- 依赖库：pandas, numpy, akshare, requests

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法
```bash
# 运行主程序
python main.py

# 或指定输出文件
python main.py --output my_result.csv

# 调整筛选参数
python main.py --max-premium 30 --min-ytm -5 --top 20
```

## 参数说明
- `--max-premium`: 最大转股溢价率(%)，默认50
- `--min-ytm`: 最小到期收益率(%)，默认-10
- `--min-volume`: 最小成交额(万元)，默认100
- `--top`: 输出前N只债券，默认30
- `--output`: 输出CSV文件名

## 选债策略说明
1. **低溢价策略**: 优先选择转股溢价率低的债券，进攻性强
2. **双低策略**: 价格低+溢价率低，兼顾安全性和进攻性
3. **高YTM策略**: 到期收益率高，偏防守
4. **综合评分**: 多因子加权打分

## 文件结构
```
cb_quant_system/
├── main.py           # 主程序入口
├── data_fetcher.py   # 数据获取模块
├── calculator.py     # 指标计算模块
├── strategy.py       # 选债策略模块
├── config.py         # 配置参数
├── requirements.txt  # 依赖列表
└── README.md         # 说明文档
```

## 注意事项
- 数据来源于公开免费接口，仅供学习研究使用
- 投资有风险，本系统不构成投资建议
- 建议在交易时段外运行，避免数据延迟

## 扩展建议
- 可添加更多因子：正股波动率、转债剩余规模、行业分类等
- 可接入数据库存储历史数据
- 可添加回测模块验证策略效果
