install:
	uv sync

run-groupa:
	uv run python main.py group-a

run-groupb:
	uv run python main.py group-b

run-admin:
	uv run python main.py admin

clean:
	rm -rf .venv __pycache__ *.pyc