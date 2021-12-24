# Copyright 2021 Yuan He (KRR-Oxford). All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Class for string matching OM system"""

from typing import Optional, List, Set
from textdistance import levenshtein
from itertools import product

from deeponto.ontology.onto_text import Tokenizer
from deeponto.ontology import Ontology
from . import OntoAlign


class StringMatch(OntoAlign):
    def __init__(
        self,
        src_onto: Ontology,
        tgt_onto: Ontology,
        tokenizer: Tokenizer,
        cand_pool_size: Optional[int] = 200,
        rel: str = "=",
        n_best: Optional[int] = 10,
        use_edit_dist: bool = False,
    ):
        super().__init__(src_onto, tgt_onto, tokenizer, cand_pool_size, rel, n_best)
        self.use_edit_dist = use_edit_dist

    def compute_mappings_for_ent(self, src_ent_id: int):
        """Compute cross-ontology mappings between source and target ontologies
        """
        # get current alignment set: src2tgt or tgt2src
        mappings = self.current_mappings()
        # get source entity contents
        src_ent_name = self.src_onto.idx2class[src_ent_id]
        src_ent_labs = self.src_onto.idx2labs[src_ent_id]
        # select target candidates and compute score for each
        tgt_cands = self.idf_select_for_ent(src_ent_id)
        for tgt_cand_id, _ in tgt_cands:
            tgt_ent_name = self.tgt_onto.idx2class[tgt_cand_id]
            tgt_ent_labs = self.tgt_onto.idx2labs[tgt_cand_id]
            if not self.use_edit_dist:
                mapping_score = int(len(self.overlap(src_ent_labs, tgt_ent_labs)) > 0)
            else:
                mapping_score = self.max_norm_edit_sim(src_ent_labs, tgt_ent_labs)
            if mapping_score > 0:
                # save mappings only with positive mapping scores
                mappings.add(self.set_mapping(src_ent_name, tgt_ent_name, mapping_score))

    @staticmethod
    def overlap(src_ent_labs: List[str], tgt_ent_labs: List[str]) -> Set:
        # TODO: the overlapped percentage could be a factor of judgement
        return set(src_ent_labs).intersection(set(tgt_ent_labs))

    @classmethod
    def max_norm_edit_sim(cls, src_ent_labs: List[str], tgt_ent_labs: List[str]) -> float:
        # save time from the special case of overlapped labels
        if cls.overlap(src_ent_labs, tgt_ent_labs):
            return 1.0
        label_pairs = product(src_ent_labs, tgt_ent_labs)
        sim_scores = [levenshtein.normalized_similarity(src, tgt) for src, tgt in label_pairs]
        return max(sim_scores)