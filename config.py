"""
项目公共配置
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()  # 自动读取项目根目录的 .env 文件

import logging
import sys
import os
from datetime import datetime

# ============================================================
# 一、路径
# ============================================================
PROJECT = Path(__file__).parent
OUTPUT = PROJECT / "output"
CHARTS = OUTPUT / "charts"

OUTPUT.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(parents=True, exist_ok=True)

RUN_MONTH = datetime.now().strftime("%Y%m")

# ============================================================
# 二、数据库连接
# ============================================================
from sqlalchemy import create_engine

def _build_engine(prefix):
    """根据环境变量前缀构建 engine。支持 mysql / mssql / sqlite"""
    db_type = os.getenv(f"{prefix}_DB_TYPE", "mysql")
    host = os.getenv(f"{prefix}_DB_HOST", "127.0.0.1")
    port = os.getenv(f"{prefix}_DB_PORT", "3306")
    user = os.getenv(f"{prefix}_DB_USER", "")
    pwd  = os.getenv(f"{prefix}_DB_PASSWORD", "")
    db   = os.getenv(f"{prefix}_DB_NAME", "")

    if db_type == "mysql":
        url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"
    elif db_type == "mssql":
        url = f"mssql+pymssql://{user}:{pwd}@{host}:{port}/{db}"
    elif db_type == "sqlite":
        url = f"sqlite:///{db}"
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")
    return create_engine(url)

def get_kingdee_engine():
    """金蝶 — 产品、客户、订单、库存"""
    return _build_engine("KINGDEE")

def get_ufida_engine():
    """用友 — 回款、财务"""
    return _build_engine("UFIDA")

def get_analysis_engine():
    """报表库 — 清洗后的结果存这里，不污染业务库"""
    return _build_engine("ANALYSIS")

# ============================================================
# 三、日志
# ============================================================
def setup_logging(name="analysis"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    log_file = OUTPUT / f"{name}_{datetime.now().strftime('%Y%m')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger

# ============================================================
# 四、Matplotlib 字体
# ============================================================
import matplotlib.pyplot as plt
import platform

if platform.system() == "Windows":
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
elif platform.system() == "Darwin":
    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC"]
plt.rcParams["axes.unicode_minus"] = False
