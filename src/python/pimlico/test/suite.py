import argparse
import sys

from pimlico.test.pipeline import run_test_suite
from pimlico.utils.logging import get_console_logger

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline test suite runner")
    parser.add_argument("suite_file", help="CSV file in which each line contains a path to a pipeline config file "
                                           "(potentially relative to test data dir), then a list of modules to test")
    parser.add_argument("--no-clean", help="Do not clean up the storage directory after running tests. By default, "
                                           "all output from the test pipelines is deleted at the end",
                        action="store_true")
    opts = parser.parse_args()

    log = get_console_logger("Test")

    with open(opts.suite_file, "r") as f:
        rows = [row.split(",") for row in f.read().splitlines() if not row.startswith("#") and len(row.strip())]
    pipelines_and_modules = [(row[0].strip(), [m.strip() for m in row[1:]]) for row in rows]
    log.info("Running {} test pipelines".format(len(pipelines_and_modules)))

    failed = run_test_suite(pipelines_and_modules, log, no_clean=opts.no_clean)
    if failed:
        log.error("Some tests did not complete successfully: {}. See above for details".format(
            ", ".join("{}[{}]".format(pipeline, ",".join(modules)) for (pipeline, modules) in failed)
        ))
    else:
        log.info("All tests completed successfully")
    sys.exit(1 if failed else 0)
