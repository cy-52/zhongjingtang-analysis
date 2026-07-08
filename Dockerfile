# 仲景堂数据分析 — Docker 镜像
# 构建: docker build -t zhongjingtang .
# 运行: docker run --env-file .env -v ./output:/app/output zhongjingtang

FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY config.py db_loader.py ./
COPY scripts/ scripts/
COPY alembic/ alembic/
COPY alembic.ini .
COPY tests/ tests/
COPY data/ data/

# 默认跑分析
CMD ["python", "scripts/main.py"]
