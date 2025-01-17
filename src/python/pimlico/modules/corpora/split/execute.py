# This file is part of Pimlico
# Copyright (C) 2020 Mark Granroth-Wilding
# Licensed under the GNU LGPL v3.0 - https://www.gnu.org/licenses/lgpl-3.0.en.html

import random

from pimlico.core.modules.base import BaseModuleExecutor
from pimlico.utils.progress import get_progress_bar


class ModuleExecutor(BaseModuleExecutor):
    def execute(self):
        input_corpus = self.info.get_input("corpus")

        set1_list = []
        set2_list = []
        output_set2_list = "doc_list2" in self.info.output_names
        # Track how many more docs are yet to be output to each set
        if self.info.options["set1_size"] > 1.:
            # A number of documents was given
            set1_remaining = int(self.info.options["set1_size"])
            if set1_remaining > len(input_corpus):
                # We tried to create a split that's bigger than the whole corpus
                # Put everything in set1, but output a warning, as it probably wasn't intended this way
                self.log.warn("Requested size of corpus split 1 (%d) is greater than the total size (%d). Split 2 "
                              "will be empty" % (set1_remaining, len(input_corpus)))
                set1_remaining = len(input_corpus)
        else:
            # A proportion of the dataset was given
            set1_remaining = len(input_corpus) * self.info.options["set1_size"]
        set2_remaining = len(input_corpus) - set1_remaining

        pbar = get_progress_bar(len(input_corpus), title="Splitting")
        # Copy over the corpus metadata from the input to start with
        # The writer will replace some values, but anything specific to the datatype should be copied
        with self.info.get_output_writer("set1", **input_corpus.metadata) as set1_writer:
            with self.info.get_output_writer("set2", **input_corpus.metadata) as set2_writer:
                for archive_name, doc_name, doc_data in pbar(input_corpus.archive_iter()):
                    if set1_remaining == 0:
                        # Must be set 2
                        put_in, lst = set2_writer, set2_list
                        output_list = output_set2_list
                    elif set2_remaining == 0:
                        # Must be set 1
                        put_in, lst = set1_writer, set1_list
                        output_list = True
                    else:
                        # Randomly choose which set to put this doc in
                        set1_prob = float(set1_remaining) / (set1_remaining + set2_remaining)
                        use_set1 = random.random() < set1_prob

                        put_in, lst = (set1_writer, set1_list) if use_set1 else (set2_writer, set2_list)
                        output_list = use_set1 or output_set2_list

                    put_in.add_document(archive_name, doc_name, doc_data)
                    if output_list:
                        lst.append(doc_name)

        # Output the list(s) of chosen docs
        with self.info.get_output_writer("doc_list1") as list_writer:
            self.log.info("Outputting set1 list to %s" % list_writer.base_dir)
            list_writer.write_list(set1_list)

        if output_set2_list:
            with self.info.get_output_writer("doc_list2") as list_writer:
                self.log.info("Outputting set2 list to %s" % list_writer.base_dir)
                list_writer.write_list(set2_list)
