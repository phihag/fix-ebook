default: test

test:
	flake8 fix-ebook.py

.PHONY: default test clean

