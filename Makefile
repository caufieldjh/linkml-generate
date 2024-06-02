# linkml-generate Makefile

RUN = poetry run

all: docs/examples.md test

test:
	$(RUN) pytest tests

serve:
	$(RUN) mkdocs serve

gh-deploy:
	$(RUN) mkdocs gh-deploy