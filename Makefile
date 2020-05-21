PYTHON?=python3.8
VENV?=./.venv/bin

.venv: .venv/bin/activate

.venv/bin/activate: setup.cfg
	test -d .venv || $(PYTHON) -m venv .venv
	$(VENV)/pip install --upgrade pip
	$(VENV)/pip install -e .
	touch $@

.venv/bin/pip-compile: .venv
	$(VENV)/pip install --upgrade pip-tools
	touch $@

.venv/.dev: dev-requirements.txt
	$(VENV)/pip install -Ur dev-requirements.txt
	touch $@

.PHONY: test
test: .venv/.dev
	$(VENV)/tox

.PHONY: test_continually
test_continually: .venv/.dev
	$(VENV)/pip install --upgrade pytest-testmon pytest-watch
	$(VENV)/ptw -- --testmon

.PHONY: precommit_update
precommit_update: .venv/.dev
	$(VENV)/pre-commit autoupdate

.PHONY: test_release
test_release: .venv/.dev distclean
	$(VENV)/python setup.py sdist bdist_wheel
	$(VENV)/twine upload --repository-url https://test.pypi.org/legacy/ dist/*

.PHONY: release
release: .venv/.dev distclean
	$(VENV)/python setup.py sdist bdist_wheel
	$(VENV)/twine upload dist/*

.PHONY: distclean
distclean:
	rm -rf dist build

.PHONY: clean-venv
clean-venv:
	rm -rf .venv

%.txt: %.in $(VENV)/pip-compile
	$(VENV)/pip-compile -v --generate-hashes --output-file $@ $<
