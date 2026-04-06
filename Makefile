run:
	cd backend && python main.py

test:
	pytest backend/testing/core/

install:
	pip install -r backend/requirements.txt
