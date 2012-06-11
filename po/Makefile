
PYFILES=$(shell find .. -name '*.py' -not -type l | sort)
LANG=fr en de nl it

MO=$(foreach l,$(LANG),mo/$(l)/LC_MESSAGES/osmose-frontend.mo)
PO=$(foreach l,$(LANG),$(l).po)

.PRECIOUS: $(PO) $(MO)

all: $(PO) $(MO)

osmose-frontend.pot: $(PYFILES)
	xgettext -cTRANSLATORS --language=Python --keyword=_ --keyword=N_ --output=osmose-frontend.pot $(PYFILES)

%.po: osmose-frontend.pot
	if test -e $@; then \
	  msgmerge -o $@ $@ $<; \
        else \
	  msginit --locale=$(patsubst %.po,%,$@) --input=$< --output=$@; \
	fi;

mo/%/LC_MESSAGES/osmose-frontend.mo: %.po
	@mkdir -p $(patsubst %/osmose-frontend.mo,%,$@)
	msgfmt --output-file=$@ $<

statistics:
	@for i in $(PO); do \
	  (msgfmt --statistics --verbose -o - $$i > /dev/null) 2>&1; \
	done