# This file is part of Pimlico
# Copyright (C) 2016 Mark Granroth-Wilding
# Licensed under the GNU GPL v3.0 - http://www.gnu.org/licenses/gpl-3.0.en.html

"""
Input reader for VRT text collections (`VeRticalized Text, as used by Korp:
<https://www.kielipankki.fi/development/korp/corpus-input-format/#VRT_file_format>`_).
Reads in files from arbitrary locations in the same way as :mod:`pimlico.modules.input.text.raw_text_files`.

"""

import os

from pimlico.core.modules.inputs import iterable_input_reader_factory
from pimlico.datatypes.vrt import VRTDocumentType
from pimlico.modules.input.text.raw_text_files.info import ModuleInfo as RawTextModuleInfo, \
    OutputType as RawTextOuputType, get_paths_from_options
from pimlico.utils.core import cached_property


class VRTOutputType(RawTextOuputType):
    """
    Output type used by reader to read the documents straight from external files.

    """
    data_point_type = VRTDocumentType

    def count_documents(self):
        """
        Counts length of corpus. Each file can contain an arbitrary number of documents.
        Should only be called after data_ready() == True.

        """
        count = 0
        for path, start, end in get_paths_from_options(self.reader_options):
            if os.path.exists(path):
                # Scan through the lines of the file to find all lines that start a new document
                with open(path, "r") as f:
                    for line in f:
                        line = line.decode(self.reader_options["encoding"])
                        if line.startswith(u"<text "):
                            count += 1
        return count

    def iter_docs_in_file(self, f):
        # Use the super method to iterate over files
        # Then we need to split each file into multiple docs
        # Note that the file could be huge, e.g. the whole corpus, so avoid reading it all into memory
        current_text = []
        for line in f:
            line = line.decode(self.reader_options["encoding"])
            if line.startswith(u"<text "):
                # Start of a new text
                # If there's anything in the buffer, there must have been a missing closing tag. Throw it away
                current_text = [line]
            elif line.startswith(u"</text>"):
                # End of text: yield it
                current_text.append(line)
                yield u"".join(current_text).strip(u"\n")
                current_text = []
            else:
                # Mid-text
                current_text.append(line)


ModuleInfo = iterable_input_reader_factory(
    dict(RawTextModuleInfo.module_options, **{
        # More options may be added here
    }),
    VRTOutputType,
    module_type_name="vrt_files_reader",
    module_readable_name="VRT annotated text files",
    execute_count=True,
)