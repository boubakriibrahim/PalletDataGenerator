# Minimal makefile for Sphinx documentation

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD  ?= sphinx-build
SOURCEDIR    = .
BUILDDIR     = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Auto-generate API documentation
apidoc:
	sphinx-apidoc -o api ../src/palletdatagenerator --force --separate

# Clean build directory
clean:
	rm -rf $(BUILDDIR)/*
	rm -rf api/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Build HTML documentation
html: apidoc
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(O)
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

# Build documentation and serve locally
serve: html
	@echo "Starting local server at http://localhost:8000"
	@cd $(BUILDDIR)/html && python -m http.server 8000

# Build PDF documentation
pdf:
	@$(SPHINXBUILD) -b latex "$(SOURCEDIR)" "$(BUILDDIR)/latex" $(SPHINXOPTS) $(O)
	@make -C $(BUILDDIR)/latex all-pdf
	@echo "PDF build finished. The PDF is in $(BUILDDIR)/latex."

# Check for broken links
linkcheck:
	@$(SPHINXBUILD) -b linkcheck "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck" $(SPHINXOPTS) $(O)
	@echo "Link check complete; look for any errors in the above output or in $(BUILDDIR)/linkcheck/output.txt."

# Check documentation coverage
coverage:
	@$(SPHINXBUILD) -b coverage "$(SOURCEDIR)" "$(BUILDDIR)/coverage" $(SPHINXOPTS) $(O)
	@echo "Coverage check complete; see $(BUILDDIR)/coverage/."

# Build documentation with all warnings as errors
strict:
	@$(SPHINXBUILD) -W -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(O)

# Live reload for development
live:
	@echo "Starting live reload server..."
	@pip install sphinx-autobuild
	@sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(O) --host 0.0.0.0 --port 8000

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
