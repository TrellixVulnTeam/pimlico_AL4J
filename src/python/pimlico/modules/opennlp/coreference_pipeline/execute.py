# This file is part of Pimlico
# Copyright (C) 2016 Mark Granroth-Wilding
# Licensed under the GNU GPL v3.0 - http://www.gnu.org/licenses/gpl-3.0.en.html

from pimlico.core.external.java import Py4JInterface, JavaProcessError
from pimlico.core.modules.execute import ModuleExecutionError
from pimlico.core.modules.map import skip_invalid
from pimlico.core.modules.map.multiproc import multiprocessing_executor_factory
from pimlico.datatypes.base import InvalidDocument
from pimlico.datatypes.coref.opennlp import Entity
from pimlico.modules.opennlp.coreference.info import WORDNET_DIR

from py4j.java_gateway import get_field


def _get_full_queue(q):
    output = []
    while not q.empty():
        output.append(q.get_nowait())
    return u"\n".join(output)


@skip_invalid
def process_document(worker, archive, filename, doc):
    interface = worker.interface
    # Resolve coreference, passing in PTB parse trees as strings
    coref_result = interface.gateway.entry_point.resolveCoreference(doc)
    if coref_result is None:
        # Coref failed, return an invalid doc
        # Fetch all output from stdout and stderr
        stdout = _get_full_queue(interface.stdout_queue)
        stderr = _get_full_queue(interface.stderr_queue)
        return InvalidDocument(
            u"opennlp_coref", u"Error running coref\nJava stdout:\n%s\nJava stderr:\n%s" % (stdout, stderr)
        )

    outputs = []
    for output_name in worker.info.output_names:
        if output_name == "coref":
            # Pull all of the information out of the java objects to get ready to store as JSON
            outputs.append([Entity.from_java_object(e) for e in get_field(coref_result, "entities")])
        elif output_name == "tokenized":
            outputs.append([sentence.split() for sentence in get_field(coref_result, "tokenizedSentences")])
        elif output_name == "pos":
            tokens = [sentence.split() for sentence in get_field(coref_result, "tokenizedSentences")]
            pos_tags = [sentence.split() for sentence in get_field(coref_result, "posTags")]
            outputs.append(zip(tokens, pos_tags))
        elif output_name == "parse":
            outputs.append(list(coref_result.getParseTrees()))
    return tuple(outputs)


def start_interface(info):
    """
    Start up a Py4J interface to a new JVM.

    """
    # Start a parser process running in the background via Py4J
    gateway_args=[
        info.sentence_model_path, info.token_model_path, info.pos_model_path, info.parse_model_path,
        info.coref_model_path
    ]
    if info.options["timeout"] is not None:
        # Set a timeout for coref tasks
        gateway_args.extend(["--timeout", str(info.options["timeout"])])

    interface = Py4JInterface(
        "pimlico.opennlp.CoreferenceResolverRawTextGateway", gateway_args=gateway_args,
        pipeline=info.pipeline, system_properties={"WNSEARCHDIR": WORDNET_DIR},
        java_opts=["-Xmx%s" % info.get_heap_memory_limit(), "-Xms%s" % info.get_heap_memory_limit()],
        print_stderr=False, print_stdout=False
    )
    try:
        interface.start()
    except JavaProcessError, e:
        raise ModuleExecutionError("error starting coref process: %s" % e)
    return interface


def worker_set_up(worker):
    worker.interface = start_interface(worker.info)


def worker_tear_down(worker):
    worker.interface.stop()


def preprocess(executor):
    if executor.info.options["timeout"] is not None:
        executor.log.info("Allow up to %d seconds for each coref job" % executor.info.options["timeout"])
    # Don't parse the parse trees, since OpenNLP does that for us, straight from the text
    executor.input_corpora[0].raw_data = True


ModuleExecutor = multiprocessing_executor_factory(
    process_document, preprocess_fn=preprocess, worker_set_up_fn=worker_set_up, worker_tear_down_fn=worker_tear_down
)
