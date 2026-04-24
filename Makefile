.PHONY: install demo clean mlflow-ui test

install:
	uv sync

demo:
	uv run oai-finance build

clean:
	rm -rf data/bronze data/silver data/gold data/synthetic artifacts mlruns

mlflow-ui:
	uv run mlflow ui --backend-store-uri file://$(PWD)/mlruns --host 127.0.0.1 --port 5000

test:
	uv run pytest -q
