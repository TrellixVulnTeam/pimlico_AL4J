"""
This module implements the concept of Dictionary -- a mapping between words and
their integer ids.

The implementation is based on Gensim, because Gensim is wonderful and there's no need to reinvent the wheel.
We don't use Gensim's data structure directly, because it's unnecessary to depend on the whole of Gensim just
for one data structure.

"""
import os
from collections import defaultdict
import itertools
from itertools import izip
import cPickle as pickle

from pimlico.datatypes.base import PimlicoDatatype, PimlicoDatatypeWriter


class Dictionary(PimlicoDatatype):
    """
    Dictionary encapsulates the mapping between normalized words and their integer ids.

    """
    def __init__(self, base_dir, pipeline, **kwargs):
        super(Dictionary, self).__init__(base_dir, pipeline, **kwargs)

    def get_data(self):
        with open(os.path.join(self.data_dir, "dictionary"), "r") as f:
            return pickle.load(f)

    def data_ready(self):
        return super(Dictionary, self).data_ready() and os.path.exists(os.path.join(self.data_dir, "dictionary"))


class DictionaryWriter(PimlicoDatatypeWriter):
    def __init__(self, base_dir):
        super(DictionaryWriter, self).__init__(base_dir)
        self.data = DictionaryData()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super(DictionaryWriter, self).__exit__(exc_type, exc_val, exc_tb)
        with open(os.path.join(self.data_dir, "dictionary"), "w") as f:
            pickle.dump(self.data, f, -1)

    def add_documents(self, documents, prune_at=2000000):
        self.data.add_documents(documents, prune_at=prune_at)

    def filter(self, threshold=None, no_above=None, limit=None):
        if threshold is None:
            threshold = 0
        if no_above is None:
            no_above = 1.
        self.data.filter_extremes(no_below=threshold, no_above=no_above, keep_n=limit)


class DictionaryData(object):
    """
    Dictionary encapsulates the mapping between normalized words and their integer ids.
    This is taken almost directly from Gensim.

    TODO: Provide a mapping to Gensim's actual Dictionary type for modules that use Gensim.

    """
    def __init__(self):
        self.token2id = {}  # token -> tokenId
        self.id2token = {}  # reverse mapping for token2id; only formed on request, to save memory
        self.dfs = {}  # document frequencies: tokenId -> in how many documents this token appeared

        self.num_docs = 0  # number of documents processed
        self.num_pos = 0  # total number of corpus positions
        self.num_nnz = 0  # total number of non-zeroes in the BOW matrix

    def __getitem__(self, tokenid):
        return self.id2token[tokenid]  # will throw for non-existent ids

    def __iter__(self):
        return iter(self.keys())

    def keys(self):
        """Return a list of all token ids."""
        return list(self.token2id.values())

    def __len__(self):
        """
        Return the number of token->id mappings in the dictionary.
        """
        return len(self.token2id)

    def __str__(self):
        some_keys = list(itertools.islice(self.token2id.iterkeys(), 5))
        return "Dictionary(%i unique tokens: %s%s)" % (len(self), some_keys, '...' if len(self) > 5 else '')

    def add_documents(self, documents, prune_at=2000000):
        """
        Update dictionary from a collection of documents. Each document is a list
        of tokens = **tokenized and normalized** strings (either utf8 or unicode).

        This is a convenience wrapper for calling `doc2bow` on each document
        with `allow_update=True`, which also prunes infrequent words, keeping the
        total number of unique words <= `prune_at`. This is to save memory on very
        large inputs. To disable this pruning, set `prune_at=None`.

        """
        for docno, document in enumerate(documents):
            # Run a regular check for pruning, once every 10k docs
            if docno % 10000 == 0 and prune_at is not None and len(self) > prune_at:
                self.filter_extremes(no_below=0, no_above=1.0, keep_n=prune_at)
            # Update dictionary with the document
            self.doc2bow(document, allow_update=True)  # ignore the result, here we only care about updating token ids

    def doc2bow(self, document, allow_update=False, return_missing=False):
        """
        Convert `document` (a list of words) into the bag-of-words format = list
        of `(token_id, token_count)` 2-tuples. Each word is assumed to be a
        **tokenized and normalized** string (either unicode or utf8-encoded). No further preprocessing
        is done on the words in `document`; apply tokenization, stemming etc. before
        calling this method.

        If `allow_update` is set, then also update dictionary in the process: create
        ids for new words. At the same time, update document frequencies -- for
        each word appearing in this document, increase its document frequency (`self.dfs`)
        by one.

        If `allow_update` is **not** set, this function is `const`, aka read-only.
        """
        if isinstance(document, basestring):
            raise TypeError("doc2bow expects an array of unicode tokens on input, not a single string")

        # Construct (word, frequency) mapping.
        counter = defaultdict(int)
        for w in document:
            counter[w if isinstance(w, unicode) else unicode(w, 'utf-8')] += 1

        token2id = self.token2id
        if allow_update or return_missing:
            missing = dict((w, freq) for w, freq in counter.iteritems() if w not in token2id)
            if allow_update:
                for w in missing:
                    # new id = number of ids made so far;
                    # NOTE this assumes there are no gaps in the id sequence!
                    token2id[w] = len(token2id)

        result = dict((token2id[w], freq) for w, freq in counter.iteritems() if w in token2id)

        if allow_update:
            self.num_docs += 1
            self.num_pos += sum(counter.itervalues())
            self.num_nnz += len(result)
            # increase document count for each unique token that appeared in the document
            dfs = self.dfs
            for tokenid in result.iterkeys():
                dfs[tokenid] = dfs.get(tokenid, 0) + 1

        # return tokenids, in ascending id order
        result = sorted(result.iteritems())
        if return_missing:
            return result, missing
        else:
            return result

    def filter_extremes(self, no_below=5, no_above=0.5, keep_n=100000):
        """
        Filter out tokens that appear in

        1. fewer than `no_below` documents (absolute number) or
        2. more than `no_above` documents (fraction of total corpus size, *not* absolute number).
        3. after (1) and (2), keep only the first `keep_n` most frequent tokens (or keep all if `None`).

        After the pruning, shrink resulting gaps in word ids.

        **Note**: Due to the gap shrinking, the same word may have a different word id before and after the call
        to this function!

        """
        no_above_abs = int(no_above * self.num_docs)  # convert fractional threshold to absolute threshold

        # determine which tokens to keep
        good_ids = (v for v in self.token2id.itervalues() if no_below <= self.dfs.get(v, 0) <= no_above_abs)
        good_ids = sorted(good_ids, key=self.dfs.get, reverse=True)
        if keep_n is not None:
            good_ids = good_ids[:keep_n]
        # do the actual filtering, then rebuild dictionary to remove gaps in ids
        self.filter_tokens(good_ids=good_ids)

    def filter_tokens(self, bad_ids=None, good_ids=None):
        """
        Remove the selected `bad_ids` tokens from all dictionary mappings, or, keep
        selected `good_ids` in the mapping and remove the rest.

        `bad_ids` and `good_ids` are collections of word ids to be removed.
        """
        if bad_ids is not None:
            bad_ids = set(bad_ids)
            self.token2id = dict((token, tokenid)
                                 for token, tokenid in self.token2id.iteritems()
                                 if tokenid not in bad_ids)
            self.dfs = dict((tokenid, freq)
                            for tokenid, freq in self.dfs.iteritems()
                            if tokenid not in bad_ids)
        if good_ids is not None:
            good_ids = set(good_ids)
            self.token2id = dict((token, tokenid)
                                 for token, tokenid in self.token2id.iteritems()
                                 if tokenid in good_ids)
            self.dfs = dict((tokenid, freq)
                            for tokenid, freq in self.dfs.iteritems()
                            if tokenid in good_ids)
        self.compactify()

    def compactify(self):
        """
        Assign new word ids to all words.

        This is done to make the ids more compact, e.g. after some tokens have
        been removed via :func:`filter_tokens` and there are gaps in the id series.
        Calling this method will remove the gaps.
        """
        # build mapping from old id -> new id
        idmap = dict(izip(self.token2id.itervalues(), xrange(len(self.token2id))))

        # reassign mappings to new ids
        self.token2id = dict((token, idmap[tokenid]) for token, tokenid in self.token2id.iteritems())
        self.id2token = {}
        self.dfs = dict((idmap[tokenid], freq) for tokenid, freq in self.dfs.iteritems())