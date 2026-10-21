# make documentation

PACKAGE=$(notdir $(CURDIR))

LOGO="https://github.com/eudoxys/.github/blob/main/eudoxys_banner.png?raw=true"
LINK="https://www.eudoxys.com/"

.PHONY: docs

docs:
	pip install --upgrade pdoc
	pdoc $(PACKAGE)/__init__.py -o $@ --logo $(LOGO) --mermaid --math --logo-link $(LINK)
