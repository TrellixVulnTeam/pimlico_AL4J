# This file is part of Pimlico
# Copyright (C) 2016 Mark Granroth-Wilding
# Licensed under the GNU GPL v3.0 - http://www.gnu.org/licenses/gpl-3.0.en.html
from pimlico.datatypes.documents import RawDocumentType
from pimlico.datatypes.tar import TarredCorpus, TarredCorpusWriter

__all__ = ["TokenizedCorpus", "TokenizedCorpusWriter"]


class TokenizedDocumentType(RawDocumentType):
    formatters = [("tokenized_doc", "pimlico.datatypes.formatters.tokenized.TokenizedDocumentFormatter")]

    def process_document(self, doc):
        return [sentence.split(u" ") for sentence in doc.split(u"\n")]


class TokenizedCorpus(TarredCorpus):
    """
    Specialized datatype for a tarred corpus that's had tokenization applied. The datatype does very little -
    the main reason for its existence is to allow modules to require that a corpus has been tokenized before
    it's given as input.

    Each document is a list of sentences. Each sentence is a list of words.

    """
    datatype_name = "tokenized"
    data_point_type = TokenizedDocumentType


class TokenizedCorpusWriter(TarredCorpusWriter):
    """
    Simple writer that takes lists of tokens and outputs them with a sentence per line and tokens separated
    by spaces.

    """
    def document_to_raw_data(self, doc):
        return u"\n".join(u" ".join(sentence) for sentence in doc)
