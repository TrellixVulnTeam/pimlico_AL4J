"""
The Pimlico Processing Toolkit (PIpelined Modular LInguistic COrpus processing) is a toolkit for building pipelines
made up of linguistic processing tasks to run on large datasets (corpora). It provides a wrappers around many
existing, widely used NLP (Natural Language Processing) tools.

"""
import os
import sys
from pimlico.core.dependencies.base import check_and_install
from pimlico.core.dependencies.core import CORE_PIMLICO_DEPENDENCIES

PIMLICO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

# Fetch current version number from PIMLICO_ROOT/admin/release.txt
with open(os.path.join(PIMLICO_ROOT, "admin", "release.txt"), "r") as releases_file:
    _lines = [r.strip() for r in releases_file.read().splitlines()]
    releases = [r[1:] for r in _lines if r.startswith("v")]
# The last listed version is the current, bleeding-edge version number
# This file used to contain all release numbers, but we now get them from git tags
# The only information given in the file now is the current version
__version__ = releases[-1]

PROJECT_ROOT = os.path.abspath(os.path.join(PIMLICO_ROOT, ".."))

LIB_DIR = os.path.join(PIMLICO_ROOT, "lib")
JAVA_LIB_DIR = os.path.join(LIB_DIR, "java")
JAVA_BUILD_JAR_DIR = os.path.join(PIMLICO_ROOT, "build", "jar")
MODEL_DIR = os.path.join(PIMLICO_ROOT, "models")
LOG_DIR = os.path.join(PIMLICO_ROOT, "log")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
EXAMPLES_DIR = os.path.join(PIMLICO_ROOT, "examples")
TEST_DATA_DIR = os.path.join(PIMLICO_ROOT, "test", "data")
TEST_STORAGE_DIR = os.path.join(PIMLICO_ROOT, "test", "storage")

# By default, we run in interative mode, assuming the user's at a terminal
# This switch tells interface components that they can't expect input from a user
# This should mean, for example, that we don't display progress bars, whose output looks
#  bad when piped to a file
# The parameter can be set using the environment variable PIM_NON_INT to 1,
#  or the cmd line switch --non-interactive
# TODO Add this to the documentation
# TODO Use this to hide progress bars, etc
# TODO Allow this to be set on the cmd line
NON_INTERACTIVE_MODE = len(os.environ.get("PIM_NON_INT", "")) > 0

def install_core_dependencies():
    # Always check that core dependencies are satisfied before running anything
    # Core dependencies are not allowed to depend on the local config, as we can't get to it at this point
    # We just pass in an empty dictionary
    unavailable = [dep for dep in CORE_PIMLICO_DEPENDENCIES if not dep.available({})]
    if len(unavailable):
        print >>sys.stderr, "Some core Pimlico dependencies are not available: %s\n" % \
                            ", ".join(dep.name for dep in unavailable)
        uninstalled = check_and_install(CORE_PIMLICO_DEPENDENCIES, {})
        if len(uninstalled):
            print >>sys.stderr, "Unable to install all core dependencies: exiting"
            sys.exit(1)
