# ---------------------------------------------------------------------------
# News Bias Summarizer — local development orchestration
# ---------------------------------------------------------------------------

SHELL := /bin/bash
.DEFAULT_GOAL := help

RUN_DIR := .run

BACKEND_DIR := backend
WEBAPI_DIR  := web-apis
WEB_DIR     := web/dist
EXT_SERVER  := extension/server
EXT_CLIENT  := extension/client

BACKEND_PORT    := 8000
WEBAPI_PORT     := 8001
WEB_PORT        := 4173
EXT_SERVER_PORT := 8008

# Node package manager for the extension services (override: make start PKG=pnpm)
PKG ?= npm

.PHONY: help install start stop restart status logs clean

# Launch one service in its own session, tracked by a pid file.
# Args: 1=name  2=workdir  3=command
define start_service
name="$(1)"; workdir="$(2)"; \
pidfile="$(RUN_DIR)/$$name.pid"; logfile="$(RUN_DIR)/$$name.log"; \
if [ -f "$$pidfile" ] && kill -0 "$$(cat "$$pidfile")" 2>/dev/null; then \
  echo "  [skip]  $$name already running (pid $$(cat "$$pidfile"))"; \
else \
  : > "$$logfile"; \
  ( cd "$$workdir" && exec setsid $(3) ) >"$$logfile" 2>&1 & \
  pid=$$!; echo "$$pid" > "$$pidfile"; \
  echo "  [up]    $$name (pid $$pid)"; \
fi
endef

help:
	@printf '%s\n' \
	  'Usage: make <target>' \
	  '' \
	  '  install   Install dependencies for every component' \
	  '  start     Run backend, web-apis, web, extension server & client' \
	  '  stop      Stop everything started by "make start"' \
	  '  restart   Stop, then start' \
	  '  status    Show which tracked services are running' \
	  '  logs      Follow all service logs (Ctrl+C to detach)' \
	  '  clean     Stop services and remove $(RUN_DIR)/'

$(RUN_DIR):
	@mkdir -p $(RUN_DIR)
	@printf '*\n' > $(RUN_DIR)/.gitignore

install:
	@echo "Installing dependencies..."
	cd $(BACKEND_DIR) && uv sync
	cd $(WEBAPI_DIR)  && uv sync
	cd $(EXT_SERVER)  && $(PKG) install
	cd $(EXT_CLIENT)  && $(PKG) install

start: $(RUN_DIR)
	@echo "Starting services..."
	@for tool in uv python3 $(PKG); do \
	  command -v $$tool >/dev/null 2>&1 || echo "  [warn]  '$$tool' not found — related service(s) may fail"; \
	done
	@$(call start_service,backend,$(BACKEND_DIR),uv run uvicorn main:app --reload --port $(BACKEND_PORT))
	@$(call start_service,web-apis,$(WEBAPI_DIR),uv run uvicorn main:app --reload --port $(WEBAPI_PORT))
	@$(call start_service,web,$(WEB_DIR),python3 -m http.server $(WEB_PORT))
	@$(call start_service,ext-server,$(EXT_SERVER),$(PKG) run dev)
	@$(call start_service,ext-client,$(EXT_CLIENT),$(PKG) run dev)
	@echo ""
	@echo "  Backend API    http://localhost:$(BACKEND_PORT)/docs"
	@echo "  Web content    http://localhost:$(WEBAPI_PORT)/docs"
	@echo "  Web frontend   http://localhost:$(WEB_PORT)/"
	@echo "  Extension srv  http://localhost:$(EXT_SERVER_PORT)/"
	@echo ""
	@echo "  Logs: $(RUN_DIR)/<name>.log    Stop: make stop"

stop:
	@if [ -d "$(RUN_DIR)" ] && ls $(RUN_DIR)/*.pid >/dev/null 2>&1; then \
	  for pidfile in $(RUN_DIR)/*.pid; do \
	    name="$$(basename "$$pidfile" .pid)"; \
	    pid="$$(cat "$$pidfile" 2>/dev/null)"; \
	    if [ -n "$$pid" ] && kill -0 "$$pid" 2>/dev/null; then \
	      kill -TERM -"$$pid" 2>/dev/null || kill -TERM "$$pid" 2>/dev/null; \
	      n=0; while kill -0 "$$pid" 2>/dev/null && [ $$n -lt 20 ]; do sleep 0.25; n=$$((n+1)); done; \
	      if kill -0 "$$pid" 2>/dev/null; then kill -KILL -"$$pid" 2>/dev/null || kill -KILL "$$pid" 2>/dev/null; fi; \
	      echo "  [down]  $$name (pid $$pid)"; \
	    else \
	      echo "  [stale] $$name (not running)"; \
	    fi; \
	    rm -f "$$pidfile"; \
	  done; \
	else \
	  echo "  nothing to stop"; \
	fi

restart: stop start

status:
	@if [ -d "$(RUN_DIR)" ] && ls $(RUN_DIR)/*.pid >/dev/null 2>&1; then \
	  for pidfile in $(RUN_DIR)/*.pid; do \
	    name="$$(basename "$$pidfile" .pid)"; \
	    pid="$$(cat "$$pidfile" 2>/dev/null)"; \
	    if [ -n "$$pid" ] && kill -0 "$$pid" 2>/dev/null; then echo "  [running] $$name (pid $$pid)"; else echo "  [stopped] $$name"; fi; \
	  done; \
	else echo "  no services tracked"; fi

logs:
	@if ls $(RUN_DIR)/*.log >/dev/null 2>&1; then tail -n 20 -f $(RUN_DIR)/*.log; else echo "  no logs yet — run 'make start'"; fi

clean: stop
	@rm -rf $(RUN_DIR)
	@echo "  cleaned $(RUN_DIR)/"
