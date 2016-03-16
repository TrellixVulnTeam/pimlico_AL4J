"""
Group the files of a multi-file iterable corpus into tar archives. This is a
standard thing to do at the start of the pipeline, since it's a handy way to
store many (potentially small) files without running into filesystem problems.

The files are simply grouped linearly into a series of tar archives such that
each (apart from the last) contains the given number.

"""
from pimlico.core.modules.base import BaseModuleInfo
from pimlico.datatypes.base import IterableDocumentCorpus
from pimlico.datatypes.tar import TarredCorpus


class ModuleInfo(BaseModuleInfo):
    module_type_name = "tar"
    module_inputs = [("documents", IterableDocumentCorpus)]
    module_outputs = [("documents", TarredCorpus)]
    module_options = [
        ("archive_size", {
            "help": "Number of documents to include in each archive (default: 1k)",
            "default": 1000,
        }),
        ("archive_basename", {
            "help": "Base name to use for archive tar files. The archive number is appended to this. "
                    "(Default: 'archive')",
            "default": "archive",
        }),
    ]