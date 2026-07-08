# 仲景堂医疗器械销售数据分析

> 数据分析助理 — 全流程数据管道项目

连接公司金蝶 ERP + 电商平台 + 财务系统的数据库，自动完成数据提取、清洗、分析、可视化，并定时推送报告。

---

## 项目结构

```
├── config.py              # 公共配置（数据库连接、日志、字体）
├── db_loader.py            # 数据加载层（SQL / Excel / CSV 统一封装）
├── scripts/
│   ├── main.py             # 主分析脚本（ETL → 分析 → 图表 → 报告）
│   └── send_report.py      # 报告推送（邮件 + 企业微信）
├── tests/
│   └── test_db_loader.py   # 自动化测试（7 项）
├── alembic/                # 数据库迁移管理
├── .github/workflows/      # CI/CD（push 自动跑测试）
├── Dockerfile              # Docker 容器化部署
├── Makefile                # 命令快捷方式
├── requirements.txt        # Python 依赖
└── data/                   # 本地数据文件
    └── dealer_orders.xlsx  # 经销商手工订单（模拟）
```

## 数据来源

| 来源 | 系统 | 取数方式 | 对应函数 |
|------|------|---------|---------|
| 产品档案 | 金蝶 MySQL | `pd.read_sql()` | `load_products()` |
| 客户档案 | 金蝶 MySQL | `pd.read_sql()` | `load_customers()` |
| 电商订单 | 小程序商城 MySQL | `pd.read_sql()` | `load_orders()` |
| 经销商订单 | 销售内勤 Excel | `pd.read_excel()` | `load_dealer_orders()` |
| 库存 | 金蝶 MySQL | `pd.read_sql()` | `load_inventory()` |
| 回款 | 用友 MySQL | `pd.read_sql()` | `load_collections()` |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 创建 .env（参考下方示例）
# 3. 运行
python scripts/main.py                  # 全量分析
python scripts/main.py --send           # 分析 + 发送报告
python scripts/main.py -c 电商          # 只看电商渠道
python scripts/main.py -r inventory     # 只看库存报告

# 4. 测试
pytest tests/ -v

# 5. Docker
docker build -t zhongjingtang .
docker run --env-file .env zhongjingtang
```

## .env 示例

```env
KINGDEE_DB_TYPE=mysql
KINGDEE_DB_HOST=127.0.0.1
KINGDEE_DB_PORT=3306
KINGDEE_DB_USER=root
KINGDEE_DB_PASSWORD=你的密码
KINGDEE_DB_NAME=mugwort

# 用友（回款）
UFIDA_DB_TYPE=mysql
UFIDA_DB_HOST=127.0.0.1
UFIDA_DB_PORT=3306
UFIDA_DB_USER=root
UFIDA_DB_PASSWORD=你的密码
UFIDA_DB_NAME=mugwort

# 报表库（清洗后数据存这里）
ANALYSIS_DB_TYPE=mysql
ANALYSIS_DB_HOST=127.0.0.1
ANALYSIS_DB_PORT=3306
ANALYSIS_DB_USER=root
ANALYSIS_DB_PASSWORD=你的密码
ANALYSIS_DB_NAME=analysis

# 邮件发送（可选）
SMTP_HOST=smtp.qq.com
SMTP_USER=你的QQ邮箱@qq.com
SMTP_PASSWORD=授权码

# 企业微信（可选）
WECHAT_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

## 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `-m` / `--month` | 分析月份 | `-m 202608` |
| `-c` / `--channel` | 只看某个渠道 | `-c 经销商` |
| `-r` / `--report` | 报告类型 | `-r inventory` |
| `--send` | 分析完自动推送报告 | `--send` |

## 分析维度

1. 月度销售趋势 & 环比
2. 产品销量 Top 10
3. 品类销售额排名
4. 客户价值分析
5. 订单状态分布
6. 库存金额 & 临期预警
7. 回款分析 & 欠款催收

## 技术栈

Python · Pandas · MySQL · SQLAlchemy · Matplotlib · Alembic · Pytest · Docker · GitHub Actions

## 开发流程

```
feature/xxx → dev → test → main
     ↑                    ↑
  Pull Request      生产环境（定时任务自动跑）
```

## License

MIT
