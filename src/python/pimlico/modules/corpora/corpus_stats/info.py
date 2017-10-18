# This file is part of Pimlico
# Copyright (C) 2016 Mark Granroth-Wilding
# Licensed under the GNU GPL v3.0 - http://www.gnu.org/licenses/gpl-3.0.en.html

"""Some basic statistics about tokenized corpora

Counts the number of tokens, sentences and distinct tokens in a corpus.

"""
from pimlico.core.modules.base import BaseModuleInfo
from pimlico.datatypes.files import NamedFile
from pimlico.datatypes.tar import TarredCorpusType
from pimlico.datatypes.tokenized import TokenizedDocumentType


class ModuleInfo(BaseModuleInfo):
    module_type_name = "corpus_stats"
    module_readable_name = "Corpus statistics"
    module_inputs = [("corpus", TarredCorpusType(TokenizedDocumentType))]
    module_outputs = [("stats", NamedFile("stats.json"))]