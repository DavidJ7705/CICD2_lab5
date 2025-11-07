# Minimal Makefile with start/stop

APP = app.main:app
PID_FILE = .uvicorn.pid

install:
	pip install -r requirements.txt

run:
	python -m uvicorn $(APP) --host 0.0.0.0 --port 8000 --reload

start:
	nohup python -m uvicorn $(APP) --host 0.0.0.0 --port 8000 --reload \
	  > .uvicorn.out 2>&1 & echo $$! > $(PID_FILE)
	@echo "Uvicorn started (PID=$$(cat $(PID_FILE))) on http://localhost:8000"

stop:
	@if [ -f $(PID_FILE) ]; then \
	  kill $$(cat $(PID_FILE)) && rm -f $(PID_FILE) && echo "Uvicorn stopped."; \
	else \
	  echo "No PID file found. Did you use 'make start'?"; \
	fi

test:
	python -m pytest -q
#
