.PHONY: test install demo clean dist

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
	git archive --format=zip --output=dist/ai_harness.zip HEAD
	@echo "Distribution archive created at dist/ai_harness.zip"