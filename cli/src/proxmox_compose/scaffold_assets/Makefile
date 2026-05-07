PYTHON ?= python

.PHONY: install-cli test-cli lint-cli

install-cli:
	pipx install --force ./cli

test-cli:
	PYTHONPATH=cli/src $(PYTHON) -m pytest cli/tests -q

lint-cli:
	PYTHONPATH=cli/src $(PYTHON) -m compileall cli/src
