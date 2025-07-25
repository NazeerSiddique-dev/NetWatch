.PHONY: init-db dev-backend dev-backend-sudo dev-frontend dev test lint clean

# Initialize database
init-db:
	PYTHONPATH=backend python3 -m app.db.init_db

# Run backend development server (normal mode — Synthetic traffic only)
dev-backend:
	PYTHONPATH=backend python3 -m app.main

# Run backend WITH root (enables Network Lab + pcap capture)
# Usage: make dev-backend-sudo
dev-backend-sudo:
	sudo COLLECTOR_MODE=pcap PYTHONPATH=backend .venv/bin/python3 -m app.main

# Run both backend and frontend in parallel (requires tmux or run in bg)
dev:
	$(MAKE) dev-backend &
	$(MAKE) dev-frontend

# Run frontend development server
dev-frontend:
	cd frontend && npm run dev

# Run backend tests
test:
	PYTHONPATH=backend pytest backend/tests -v

# Run linting
lint:
	cd backend && ruff check .

# Clean up caches
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
