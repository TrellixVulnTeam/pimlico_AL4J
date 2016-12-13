# This file is part of Pimlico
# Copyright (C) 2016 Mark Granroth-Wilding
# Licensed under the GNU GPL v3.0 - http://www.gnu.org/licenses/gpl-3.0.en.html
from textwrap import wrap

from pimlico.core.config import print_missing_dependencies, get_dependencies
from pimlico.core.dependencies.base import install_dependencies
from pimlico.utils.format import title_box


def check_cmd(pipeline, opts):
    print "DEPRECATED:"
    print "The check command with modules specified is now deprecated."
    print "Using the status command is the preferable way to a pipeline can be loaded"
    print "Using the run command, with --dry-run switch, is the preferable way to check modules are ready to run"
    print

    # Metadata has already been loaded if we've got this far
    print "All module metadata loaded successfully"

    # Output what variants are available and say which we're checking
    print "Available pipeline variants: %s" % ", ".join(["main"] + pipeline.available_variants)
    print "Checking variant '%s'\n" % pipeline.variant

    if opts.modules:
        if "all" in opts.modules:
            # Check all modules
            modules = pipeline.modules
        else:
            modules = opts.modules
        passed = print_missing_dependencies(pipeline, modules)
        
        if passed:
            for module_name in modules:
                # Check for remaining execution barriers
                problems = pipeline[module_name].check_ready_to_run()
                if len(problems):
                    for problem_name, problem_desc in problems:
                        print "Module '%s' cannot run: %s\n  %s" % \
                              (module_name, problem_name, "\n  ".join(wrap(problem_desc, 100)))
                    passed = False
            if passed:
                print "Runtime dependency checks successful for modules: %s" % ", ".join(modules)


def install_cmd(pipeline, opts):
    """
    Install missing dependencies.

    """
    if "all" in opts.modules:
        # Install for all modules
        modules = None
    else:
        modules = opts.modules
    install_dependencies(pipeline, modules, trust_downloaded_archives=opts.trust_downloaded)


def deps_cmd(pipeline, opts):
    """
    Output information about module dependencies.

    """
    if "all" in opts.modules or len(opts.modules) == 0:
        # Install for all modules
        modules = None
    else:
        modules = opts.modules
    deps = get_dependencies(pipeline, modules, recursive=True)

    for dep in deps:
        print
        print title_box(dep.name.capitalize())
        if dep.available():
            print "Installed"
            print "Version: %s" % dep.get_installed_version()
        elif dep.installable():
            print "Can be automatically installed with the 'install' command"
        else:
            print "Cannot be automatically installed"
            print dep.installation_instructions()
