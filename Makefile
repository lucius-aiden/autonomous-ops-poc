SHELL := /bin/bash
export PATH := $(HOME)/.local/bin:$(PATH)
export KUBECONFIG := $(HOME)/.kube/config

.PHONY: sandbox-up sandbox-status sandbox-test sandbox-reset sandbox-down unit-test

sandbox-up:
	./scripts/sandbox-up.sh

sandbox-status:
	./scripts/sandbox-status.sh

sandbox-test:
	PYTHONPATH=src python3 scripts/live_smoke.py

sandbox-reset:
	./scripts/sandbox-reset.sh

sandbox-down:
	./scripts/sandbox-down.sh

unit-test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
