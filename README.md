# 可转债量化选债系统 (Convertible Bond Quantitative Selection System)

## 简介
本系统用于中国可转债市场的量化选债，通过获取实时数据、计算关键指标、实施筛选策略来辅助投资决策。

## 功能特点
- 获取全市场可转债实时数据（使用Akshare免费数据源）
- 计算关键量化指标：转股溢价率、到期收益率、转股价值、纯债价值等
- 多种选债策略：双低策略、高YTM策略、下修博弈策略、卡叔2026策略、盛唐估值策略
- 风险过滤和流动性筛选
- 汇总报告生成（Markdown格式）
- 结果导出为CSV文件

## 环境要求
- Python 3.8+
- 依赖库：pandas, numpy, akshare, requests, scipy

## 安装依赖
```bash
cd cb_quant_system

# 创建虚拟环境（首次使用）
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 快速开始
```bash
# 进入项目目录并激活虚拟环境
cd cb_quant_system
source venv/bin/activate

# 生成汇总报告（推荐，包含所有策略）
python report.py

# 运行单一策略
python main.py --strategy double_low_filter
```

## 策略使用

### 1. 双低策略
筛选标准：
- 价格区间：100-120元（避免高价股性风险）
- 转股溢价率：<20%（确保股性跟随能力）
- 剩余规模：<15亿元（提升资金关注度）

```bash
python main.py --strategy double_low_filter --no-filter
```

### 2. 高YTM策略
筛选标准：
- YTM > 3%（高于同期国债收益率）
- 信用评级 ≥ AA（规避违约风险）
- 剩余期限 > 2年（避免短期流动性冲击）

```bash
python main.py --strategy high_ytm_filter --no-filter
```

### 3. 下修博弈策略
筛选标准：
- 剩余期限 < 2年（促转股压力大）
- 未转股比例 > 70%（避免到期偿债压力）
- 高溢价率（有下修空间）

```bash
python main.py --strategy xiaxiu --no-filter
```

### 4. 卡叔2026策略
来源于卡叔2026年可转债投资策略，包含四类转债筛选：
- **第一类**：小市值高溢价距离保本位置不远 - 博弈下修
- **第二类**：绝对防御临期债 - 低期权价值、质地安全
- **第三类**：大股东未减持 - 可能先下修再减持
- **第四类**：存续期2年附近 - 上市公司开始重视促转股

```bash
python main.py --strategy kashu2026
```

### 5. 盛唐估值策略
基于盛唐风物的可转债估值模型：

**专业版** - BS模型估值，筛选低估+溢价率<50%的转债
```
转债估值 = max(债底,回售价值) + 转股期权价值 + 下修期权价值 - 强赎损失
```

**简化版** - 低溢价偏离债池，输出格式类似盛唐原版
```bash
python main.py --strategy shengtang --no-filter
```

### 6. 其他基础策略
```bash
# 综合评分策略（默认）
python main.py --strategy composite

# 低溢价策略 - 进攻性强，适合看好正股
python main.py --strategy low_premium

# 双低策略（基础版）
python main.py --strategy double_low

# 高YTM策略（基础版）
python main.py --strategy high_ytm

# 运行所有基础策略
python main.py --strategy all
```

## 汇总报告
一键生成包含所有策略的Markdown报告：
```bash
python report.py
```

报告包含：
1. 市场概览
2. 双低策略筛选结果
3. 高YTM策略筛选结果
4. 下修博弈策略筛选结果
5. 卡叔2026策略（四大类）
6. 盛唐估值策略（专业版+简化版）
7. 综合评分策略
8. 低溢价策略

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
| 震荡市 | double_low_filter, kashu2026 | 攻守兼备 |
| 熊市/防守 | high_ytm_filter, shengtang | 注重安全边际 |
| 博弈下修 | xiaxiu, kashu2026 | 专注下修机会 |
| 寻找低估 | shengtang | 量化估值模型 |

## 文件结构
```
cb_quant_system/
├── main.py                    # 主程序入口
├── report.py                  # 汇总报告生成
├── data_fetcher.py            # 数据获取模块
├── calculator.py              # 指标计算模块
├── strategy.py                # 基础选债策略
├── strategy_double_low.py     # 双低策略
├── strategy_high_ytm.py       # 高YTM策略
├── strategy_xiaxiu.py         # 下修博弈策略
├── strategy_kashu2026.py      # 卡叔2026策略
├── strategy_shengtang.py      # 盛唐估值策略（专业版）
├── strategy_shengtang_simple.py  # 盛唐估值策略（简化版）
├── config.py                  # 配置参数
├── utils.py                   # 工具函数
└── requirements.txt           # 依赖列表
```

## 注意事项
- 数据来源于公开免费接口，仅供学习研究使用
- 投资有风险，本系统不构成投资建议
- 建议在交易时段外运行，避免数据延迟
- 盛唐策略计算较慢，请耐心等待

## 扩展建议
- 可添加更多因子：正股波动率、转债剩余规模、行业分类等
- 可接入数据库存储历史数据
- 可添加回测模块验证策略效果
