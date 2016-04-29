"""
`CAEVO <http://www.usna.edu/Users/cs/nchamber/caevo/>`_ is Nate Chambers' CAscading EVent Ordering system,
a tool for extracting events of many types from text and ordering them.

`CAEVO is open source <https://github.com/nchambers/caevo>`_, implemented in Java, so is easily integrated
into Pimlico using Py4J.

.. todo::

   The implementation of this module is incomplete. I've mostly written the Py4J gateway, but not the Python side yet.

"""
import os

from pimlico.core.external.java import check_java_dependency, DependencyCheckerError
from pimlico.core.modules.base import DependencyError
from pimlico.core.modules.map import DocumentMapModuleInfo
from pimlico.core.modules.options import str_to_bool
from pimlico.core.paths import abs_path_or_model_dir_path
from pimlico.datatypes.parse.dependency import CoNLLDependencyParseInputCorpus
from pimlico.datatypes.tar import TarredCorpus, TarredCorpusWriter


class ModuleInfo(DocumentMapModuleInfo):
    module_type_name = "caevo"
    module_readable_name = "CAEVO event extractor"
    module_inputs = [("documents", CoNLLDependencyParseInputCorpus)]
    module_outputs = [("parsed", TarredCorpus)]
    module_options = {
        "model": {
            "help": "Filename of parsing model, or path to the file. If just a filename, assumed to be Malt models "
                    "dir (models/malt). Default: engmalt.linear-1.7.mco, which can be acquired by 'make malt' in the "
                    "models dir",
            "default": "engmalt.linear-1.7.mco",
        },
        "no_gzip": {
            "help": "By default, we gzip each document in the output data. If you don't do this, the output can get "
                    "very large, since it's quite a verbose output format",
            "type": str_to_bool,
            "default": False,
        }
    }

    def __init__(self, *args, **kwargs):
        super(ModuleInfo, self).__init__(*args, **kwargs)
        # Postprocess model option
        self.model_path = abs_path_or_model_dir_path(self.options["model"], "malt")

    def check_runtime_dependencies(self):
        missing_dependencies = []

        # Make sure the model is available
        if not os.path.exists(self.model_path):
            missing_dependencies.append(
                ("Malt parser model", self.module_name, "Parsing model file doesn't exists: %s" % self.model_path)
            )

        # Check whether the OpenNLP POS tagger is available
        try:
            class_name = "pimlico.malt.ParserGateway"
            try:
                check_java_dependency(class_name)
            except DependencyError:
                missing_dependencies.append(("Malt parser wrapper",
                                             self.module_name,
                                             "Couldn't load %s. Build the Malt Java wrapper module provided with "
                                             "Pimlico ('ant malt')" % class_name))

            class_name = "org.maltparser.concurrent.ConcurrentMaltParserService"
            try:
                check_java_dependency(class_name)
            except DependencyError:
                missing_dependencies.append(("Malt parser jar",
                                             self.module_name,
                                             "Couldn't load %s. Install Malt by running 'make malt' in Java lib dir" %
                                             class_name))
        except DependencyCheckerError, e:
            missing_dependencies.append(("Java dependency checker", self.module_name, str(e)))

        missing_dependencies.extend(super(ModuleInfo, self).check_runtime_dependencies())
        return missing_dependencies

    def get_writer(self, output_name, output_dir, append=False):
        return TarredCorpusWriter(output_dir, append=append, gzip=not self.options["no_gzip"])