# Configuration file for the Sphinx documentation builder.

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))

# -- Project information -----------------------------------------------------
project = "PalletDataGenerator"
copyright = "2025, Ibrahim Boubakri"
author = "Ibrahim Boubakri"

# The full version, including alpha/beta/rc tags
try:
    from palletdatagenerator import __version__

    release = __version__
    version = __version__
except ImportError:
    # Fallback if package is not installed
    release = "0.1.3"
    version = "0.1.3"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.githubpages",
    "myst_parser",  # For Markdown support
    "sphinx_rtd_theme",
    "sphinx_copybutton",
    "sphinxext.opengraph",
]

# MyST parser configuration for Markdown support
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

# Source file suffixes: map to parser names to avoid "None is not a valid filetype" warnings
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Mock imports for modules that aren't available in CI (Blender/Python API)
autodoc_mock_imports = [
    "bpy",
    "bpy_extras",
    "bmesh",
    "mathutils",
    "addon_utils",
    "palletdatagenerator.core",
    "palletdatagenerator.core.renderer",
    "palletdatagenerator.core.generator",
    "palletdatagenerator.core.config_loader",
    "palletdatagenerator.exporters",
    "palletdatagenerator.exporters.coco",
    "palletdatagenerator.exporters.voc",
    "palletdatagenerator.exporters.yolo",
]

# Suppress autodoc import warnings so docs can be built without Blender installed
# Suppress autodoc import warnings so docs can be built without Blender installed
# Also suppress autosummary and nitpicky reference warnings which CI treats as errors
suppress_warnings = [
    "autodoc.import_object",
    "autodoc.failed-import",
    "autosummary",  # suppress autosummary generation import warnings
    "myst.xref_missing",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The master toctree document.
master_doc = "index"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = "sphinx_rtd_theme"

# Theme options
html_theme_options = {
    "canonical_url": "",
    "analytics_id": "",
    "logo_only": False,
    # "display_version": True,  # removed: unsupported by current theme version
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
    "style_nav_header_background": "#2980B9",
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Custom CSS
html_css_files = [
    "custom.css",
]

# Custom JavaScript
html_js_files = []

# HTML context for templating
html_context = {
    "display_github": True,
    "github_user": "boubakriibrahim",
    "github_repo": "PalletDataGenerator",
    "github_version": "main",
    "conf_py_path": "/docs/",
    "source_suffix": source_suffix,
}

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "10pt",
    "preamble": "",
    "fncychap": "",
    "fontpkg": "",
}

# Grouping the document tree into LaTeX files.
latex_documents = [
    (
        master_doc,
        "PalletDataGenerator.tex",
        "PalletDataGenerator Documentation",
        "PalletDataGenerator Contributors",
        "manual",
    ),
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page.
man_pages = [
    (
        master_doc,
        "palletdatagenerator",
        "Pallet Data Generator Documentation",
        [author],
        1,
    )
]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files.
texinfo_documents = [
    (
        master_doc,
        "PalletDataGenerator",
        "Pallet Data Generator Documentation",
        author,
        "PalletDataGenerator",
        "Generate synthetic pallet datasets using Blender.",
        "Miscellaneous",
    ),
]

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Autosummary settings
autosummary_generate = True
autosummary_generate_overwrite = False

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
}

# Todo extension settings
todo_include_todos = True

# Copy button configuration
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# GitHub Pages configuration
html_baseurl = "https://boubakriibrahim.github.io/PalletDataGenerator/"
