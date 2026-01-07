# 可转债量化选债系统 (Convertible Bond Quantitative Selection System)

## 简介
本系统用于中国可转债市场的量化选债，通过获取实时数据、计算关键指标、实施筛选策略来辅助投资决策。

## 功能特点
- 获取全市场可转债实时数据（使用Akshare免费数据源）
- 计算关键量化指标：转股溢价率、到期收益率、转股价值、纯债价值等
- 多种选债策略：基础策略、卡叔2026策略、盛唐估值策略
- 风险过滤和流动性筛选
- 结果导出为CSV文件

## 环境要求
- Python 3.8+
- 依赖库：pandas, numpy, akshare, requests, scipy

## 安装依赖
```bash
pip install -r requirements.txt
```

## 快速开始
```bash
cd cb_quant_system

# 运行默认策略（综合评分）
python main.py

# 指定输出文件
python main.py --output my_result.csv
```

## 策略使用

### 1. 基础策略
```bash
# 综合评分策略（默认）
python main.py --strategy composite

# 低溢价策略 - 进攻性强，适合看好正股
python main.py --strategy low_premium

# 双低策略 - 价格低+溢价率低，攻守兼备
python main.py --strategy double_low

# 高YTM策略 - 偏防守，追求债底保护
python main.py --strategy high_ytm

# 价值挖掘策略 - 寻找低估转债
python main.py --strategy value

# 运行所有基础策略
python main.py --strategy all
```

### 2. 卡叔2026策略
来源于卡叔2026年可转债投资策略，包含四类转债筛选：
- **第一类**：小市值高溢价距离保本位置不远 - 博弈下修
- **第二类**：绝对防御临期债 - 低期权价值、质地安全
- **第三类**：大股东未减持 - 可能先下修再减持
- **第四类**：存续期2年附近 - 上市公司开始重视促转股

```bash
# 运行卡叔2026策略
python main.py --strategy kashu2026

# 调整输出数量
python main.py --strategy kashu2026 --top 15
```

### 3. 盛唐估值策略
基于盛唐风物的可转债估值模型，核心公式：
```
转债估值 = max(到期折现,回售折现) + 正常转股认购价值 + 下修转股组合期权价值 – 强赎认购损失
```

五大估值组成：
- 到期折现（债底）- 用信用债利率折现
- 回售折现 - 考虑回售触发概率
- 正常转股认购价值 - BS模型计算
- 下修转股组合期权价值 - 下修-转股联合过程估值
- 强赎认购损失 - 强赎导致的期权价值损失

```bash
# 运行盛唐策略（按低估程度排序）
python main.py --strategy shengtang

# 输出更多结果
python main.py --strategy shengtang --top 30
```

## 参数说明
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--strategy` | 选债策略 | composite |
| `--max-premium` | 最大转股溢价率(%) | 50 |
| `--min-ytm` | 最小到期收益率(%) | -10 |
| `--min-volume` | 最小成交额(万元) | 100 |
| `--max-price` | 最大价格 | 150 |
| `--min-price` | 最小价格 | 90 |
| `--top` | 输出前N只债券 | 30 |
| `--output` | 输出CSV文件名 | cb_selection_result.csv |
| `--no-filter` | 不进行基础筛选 | - |

## 策略选择建议
| 市场环境 | 推荐策略 | 说明 |
|----------|----------|------|
| 牛市/看好正股 | low_premium | 低溢价进攻性强 |
| 震荡市 | double_low, kashu2026 | 攻守兼备 |
| 熊市/防守 | high_ytm, shengtang | 注重安全边际 |
| 博弈下修 | kashu2026 | 专注下修机会 |
| 寻找低估 | shengtang | 量化估值模型 |

## 文件结构
```
cb_quant_system/
├── main.py              # 主程序入口
├── data_fetcher.py      # 数据获取模块
├── calculator.py        # 指标计算模块
├── strategy.py          # 基础选债策略
├── strategy_kashu2026.py   # 卡叔2026策略
├── strategy_shengtang.py   # 盛唐估值策略
├── config.py            # 配置参数
├── utils.py             # 工具函数
├── requirements.txt     # 依赖列表
└── README.md            # 说明文档
```

## TODO
- [ ] 双低策略优化
- [ ] 三低策略（价格低+溢价率低+规模低）
- [ ] 高息策略

## 注意事项
- 数据来源于公开免费接口，仅供学习研究使用
- 投资有风险，本系统不构成投资建议
- 建议在交易时段外运行，避免数据延迟
- 盛唐策略计算较慢，请耐心等待

## 扩展建议
- 可添加更多因子：正股波动率、转债剩余规模、行业分类等
- 可接入数据库存储历史数据
- 可添加回测模块验证策略效果
