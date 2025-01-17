# This file is part of Pimlico
# Copyright (C) 2020 Mark Granroth-Wilding
# Licensed under the GNU LGPL v3.0 - https://www.gnu.org/licenses/lgpl-3.0.en.html

"""
Word2vec embedding learning algorithm, using `Gensim <https://radimrehurek.com/gensim/>`_'s implementation.

Find out more about `word2vec <https://code.google.com/archive/p/word2vec/>`_.

This module is simply a wrapper to call `Gensim Python (+C) <https://radimrehurek.com/gensim/models/word2vec.html>`_'s
implementation of word2vec on a Pimlico corpus.

Does not support Python 2 since Gensim has dropped Python 2 support.

"""
from pimlico.core.dependencies.python import PythonPackageOnPip, gensim_dependency
from pimlico.core.modules.base import BaseModuleInfo
from pimlico.datatypes import GroupedCorpus, Embeddings
from pimlico.datatypes.corpora.tokenized import TokenizedDocumentType


class ModuleInfo(BaseModuleInfo):
    module_type_name = "word2vec"
    module_readable_name = "Word2vec embedding trainer"
    module_inputs = [("text", GroupedCorpus(TokenizedDocumentType()))]
    module_outputs = [("model", Embeddings())]
    module_options = {
        "min_count": {
            "help": "word2vec's min_count option: prunes the dictionary of words that appear fewer than this number "
                    "of times in the corpus. Default: 5",
            "type": int,
            "default": 5,
        },
        "size": {
            "help": "number of dimensions in learned vectors. Default: 200",
            "type": int,
            "default": 200,
        },
        "iters": {
            "help": "number of iterations over the data to perform. Default: 5",
            "type": int,
            "default": 5,
        },
        "negative_samples": {
            "help": "number of negative samples to include per positive. Default: 5",
            "type": int,
            "default": 5,
        },
    }
    module_supports_python2 = False

    def __init__(self, module_name, pipeline, **kwargs):
        super(ModuleInfo, self).__init__(module_name, pipeline, **kwargs)

    def get_software_dependencies(self):
        return super(ModuleInfo, self).get_software_dependencies() + [gensim_dependency]
