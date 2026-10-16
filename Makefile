.PHONY: test backend-test frontend-test
test: backend-test frontend-test
backend-test:
	python -m pytest -q
frontend-test:
	npm test -- --run
