from pimlico.cli.browser.formatter import load_formatter
from pimlico.core.modules.base import TypeCheckError
from pimlico.core.modules.execute import ModuleExecutionError
from pimlico.core.modules.map.multiproc import multiprocessing_executor_factory


def worker_setup(worker):
    # Prepare a formatter to format each document
    input_dataset = worker.info.get_input("corpus")
    try:
        worker.formatter = load_formatter(input_dataset, worker.info.options["formatter"])
    except (TypeError, TypeCheckError), e:
        raise ModuleExecutionError("error loading formatter: %s" % e)


def process_document(worker, archive_name, doc_name, doc):
    return worker.formatter.format_document(doc)


ModuleExecutor = multiprocessing_executor_factory(process_document, worker_set_up_fn=worker_setup)
