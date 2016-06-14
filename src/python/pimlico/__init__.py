import os
import sys
from pimlico.core.dependencies.base import check_and_install
from pimlico.core.dependencies.core import CORE_PIMLICO_DEPENDENCIES

__version__ = "0.2.1"

PIMLICO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

PROJECT_ROOT = os.path.abspath(os.path.join(PIMLICO_ROOT, ".."))

LIB_DIR = os.path.join(PIMLICO_ROOT, "lib")
JAVA_LIB_DIR = os.path.join(LIB_DIR, "java")
JAVA_BUILD_JAR_DIR = os.path.join(PIMLICO_ROOT, "build", "jar")
MODEL_DIR = os.path.join(PIMLICO_ROOT, "models")
LOG_DIR = os.path.join(PIMLICO_ROOT, "log")


def install_core_dependencies():
    # Always check that core dependencies are satisfied before running anything
    unavailable = [dep for dep in CORE_PIMLICO_DEPENDENCIES if not dep.available()]
    if len(unavailable):
        print >>sys.stderr, "Some core Pimlico dependencies are not available: %s\n" % \
                            ", ".join(dep.name for dep in unavailable)
        uninstalled = check_and_install(CORE_PIMLICO_DEPENDENCIES)
        if len(uninstalled):
            print >>sys.stderr, "Unable to install all core dependencies: exiting"
            sys.exit(1)
