
.PHONY: all
all: help

.PHONY: help
help:
	@ echo "Please give a target. Choices are:"
	@ echo "   test -> run all unittests"
	@ echo "   dev  -> installs this project in local virtual environment"
	@ echo "   venv -> update (and if needed initialize) the virual environment"

.PHONY: dev
dev: venv
	.venv/bin/pip install --editable .
	@ echo "Everything is set up for development."
	@ echo "Please switch with 'source .venv/bin/activate'"

.PHONY: test
test: venv
	.venv/bin/python -m unittest

# Initialize the virtual environment, if needed
.venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip

# Install and keep in sync with the requirements
.venv/bin/activate: requirements.txt .venv
	.venv/bin/pip install -Ur requirements.txt
	touch .venv/bin/activate

.PHONY: venv
venv: .venv/bin/activate
