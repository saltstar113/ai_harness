.PHONY: test install demo clean dist docker-build docker-run

test:
	pytest tests/ -v

install:
	pip install -r requirements.txt

demo:
	python demo.py

clean:
	rm -rf __pycache__ .pytest_cache dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

dist:
	mkdir -p dist
	git archive --format=zip --output=dist/ai_harness.zip HEAD
	@echo "Distribution archive created at dist/ai_harness.zip"

docker-build:
	docker build -t ai_harness .

docker-run:
	docker run -it --rm -v $(PWD)/workspace:/workspace ai_harness