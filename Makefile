# 仲景堂数据分析项目 — 命令快捷方式
# 用法: make test  /  make run  /  make send

.PHONY: test run send db lint clean

test:
	pytest tests/ -v --tb=short

run:
	python scripts/main.py

send:
	python scripts/main.py --send

db:
	python -m alembic upgrade head

lint:
	python -m pytest tests/ -v --tb=line

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf output/charts/*.png
