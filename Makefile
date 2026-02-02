# make documentation

PACKAGE=$(basename $(PWD))

# valid options are --debug and --refresh
CACHE_OPTIONS=--debug
AGGREGATE=elec_net_MW 2020

LOGO="https://github.com/eudoxys/.github/blob/main/eudoxys_banner.png?raw=true"
LINK="https://www.eudoxys.com/"

docs: $(PACKAGE)/__init__.py
	pip install --upgrade pdoc
	pdoc $< -o $@ --logo $(LOGO) --mermaid --math --logo-link $(LINK)

$(PACKAGE)/__init__.py: $(filter-out $(wildcard $(PACKAGE)/_*.py),$(wildcard $(PACKAGE)/*.py))
