.PHONY: install dev run backtest dashboard test lint clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

run:
	python scripts/run_bot.py

backtest:
	python scripts/run_backtest.py

dashboard:
	streamlit run stockbot/dashboard/app.py --server.port 8501

test:
	pytest tests/ -v

lint:
	ruff check stockbot/ tests/
	ruff format --check stockbot/ tests/

format:
	ruff check --fix stockbot/ tests/
	ruff format stockbot/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf build/ dist/ *.egg-info/
