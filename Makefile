venv = venv
python = python3
pip = $(venv)/bin/pip
# raise non-zero exit codes in pipes
SHELL = /bin/bash -o pipefail

all: lint test

# check the venv and run pylint
.PHONY: lint
lint: venv-dev .lint

# check the venv and run the test-suite
.PHONY: test
test: venv-dev .test


# cleanup
.PHONY: clean
clean:
	@echo "Remove the local cache, venv and compiled Python files"
	@rm -rf \
		.*cache \
		venv \
		`find . -name __pycache__`


### internal, house keeping targets ###

# house keeping: update the Jenkinsfile
Jenkinsfile: tools/gen_Jenkinsfile.py
	@$(python) tools/gen_Jenkinsfile.py

# internal: ensure an existing venv
venv:
	${python} -m venv $(venv)

# internal: check for `pip-compile` and ensure an existing cache directory
.PHONY: .gen-requirements
.gen-requirements: venv
	@if [ ! -d $(venv)/lib/*/site-packages/piptools ]; then \
		$(pip) install -q pip-tools; fi
	@if [ ! -d .cache ]; then mkdir .cache; fi

# house keeping: update `requirements-dev.txt`:
.PHONY: gen-requirements-dev
gen-requirements-dev: .gen-requirements
	CUSTOM_COMPILE_COMMAND="make gen-requirements-dev" \
	    $(venv)/bin/pip-compile \
	        --upgrade \
	        --no-annotate \
            --no-index \
            --no-emit-trusted-host \
	        requirements-dev.in
	@sed -i 's#-e file://$(PWD)#-e .#' requirements-dev.txt

# internal: ensure a venv with latest dev requirements
.PHONY: venv-dev
venv-dev: venv/dev
venv/dev: venv requirements-dev.txt
	$(pip) install --requirement requirements-dev.txt
	@touch venv/dev

# internal: run pylint
.PHONY: .lint
.lint:
	$(venv)/bin/pylint --score=no reparser

# internal: run the test-suite
.PHONY: .test
.test:
	$(venv)/bin/pytest -vvv tests
