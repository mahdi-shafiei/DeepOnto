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
"""Class for processing thesarus of "synonyms" and "non-synonyms" extracted from ontologies

Synonym pairs (labels for the same class) are guaranteed to have:
1. Reflexivity (identity synonyms): for class label1 => ADD (label1, label1);
2. Symmetricality: ADD (label1, label2) => ADD (label2, label1);
3. Transitivity (Optional, not used in the original BERTMap): ADD (label1, label2), (label2, label3) => ADD (label1, label3)

Non-synonyms are of huge sampling space, and we do not care about any of the above properties but there are two types:
1. Soft: labels from two different (atomic) classes;
2. Hard: labels from two logically disjoint (atomic) classes (sibling classes in BERTMap).

For cross-ontology level, given a small set of mappings:
1. Synonyms are extracted from label pairs of aligned classes;
2. Non-synonyms are extracted from label pairs of mismatched classes (w.r.t the given mappings).

Thoughts for future: 
1. Should we consider using equivalence axioms, e.g., (Apple, Fruit & RedColor)? Or leave it for prompts?
2. 
"""

from __future__ import annotations

import networkx as nx
import itertools
import random
from typing import List, Set, Tuple, Optional, Iterable, TYPE_CHECKING
from pyats.datastructures import AttrDict

from deeponto import SavedObj
from deeponto.utils import uniqify

# to avoid circular imports
if TYPE_CHECKING:
    from deeponto.onto import Ontology
    from deeponto.onto.mapping import OntoMappings


class Thesaurus(SavedObj):
    def __init__(self):
        # note that reflexivity and symmetricality have been assumed by
        # e.g., if a class C has labels {x, y}, we include (x, x), (y, y)
        # for reflexivity; and (x, y), (y, x) for symmetricality.
        self.sections = []
        self.merged_section = dict()
        super().__init__("thesaurus")

    def __call__(self, *ontos: Ontology, apply_transitivity_to_each: bool = False):
        """Create a new Thesaurus for given ontologies
        """
        self.__init__()
        self.add_synonyms_from_ontos(*ontos, apply_transitivity_to_each=apply_transitivity_to_each)
        print(self)

    def __str__(self) -> str:
        self.info = AttrDict(
            {
                "onto_names": [section.onto_name for section in self.sections],
                "section_sizes": [section.num_synonym_groups for section in self.sections],
            }
        )
        self.info.total_size = sum(self.info.section_sizes)
        if self.merged_section:
            self.info.merged_total_size = self.merged_section.num_synonym_groups
            self.info.reduced = self.info.total_size - self.info.merged_total_size
        return super().report(**self.info)

    def create_merged_section(self):
        all_synonym_groups = [section.synonym_groups for section in self.sections]
        merged_synonym_groups = self.merge_synonyms_by_transitivity(*all_synonym_groups)
        self.merged_section = AttrDict(
            {
                "num_synonym_groups": len(merged_synonym_groups),
                "synonym_groups": merged_synonym_groups,
            }
        )

    ##################################################################################
    ###                   extract synonyms from an ontology                        ###
    ##################################################################################

    def add_synonyms_from_ontos(self, *ontos: Ontology, apply_transitivity_to_each: bool = False):
        """Add synonyms from each input ontology into a "section"
        """
        for onto in ontos:
            synonym_groups = [set(v) for v in onto.idx2labs.values()]
            if apply_transitivity_to_each:
                synonym_groups = self.merge_synonyms_by_transitivity(synonym_groups)
            new_section = AttrDict(
                {
                    "onto_name": "[intra-onto]: " + onto.owl.name,
                    "onto_info": str(onto),
                    "num_synonym_groups": len(synonym_groups),
                    "synonym_groups": synonym_groups,
                }
            )
            self.sections.append(new_section)
            print(f"Add {new_section.num_synonym_groups} synonyms from the following ontology:\n")
            print(f"{new_section.onto_info}")
        self.create_merged_section()

    def add_matched_synonyms_from_mappings(
        self,
        src_onto: Ontology,
        tgt_onto: Ontology,
        known_mappings: OntoMappings,
        apply_transitivity_to_each: bool = False,
    ) -> List[Tuple[Set[str], Set[str]]]:
        """Add aligned synonym groups from given mappings. The merged synonyms are included as a section 
        and returning aligned but not merged src and tgt synonym groups with: (src_synonyms, tgt_synonyms) 
        for cross-ontology negative sampling.
        """
        synonym_group_pairs = []
        synonym_groups = []
        for src_ent, tgt_ent_dict in known_mappings.ranked.items():
            src_ent_labels = src_onto.idx2labs[src_onto.class2idx[src_ent]]
            for tgt_ent in tgt_ent_dict.keys():
                tgt_ent_labels = tgt_onto.idx2labs[tgt_onto.class2idx[tgt_ent]]
            # merged cross-onto synonym group where labels of aligned classes are synonymous
            synonym_group_pairs.append(
                (set(src_ent_labels), set(tgt_ent_labels))
            )  # form a synonym group pair with known ontology source
            synonym_groups.append(
                set(src_ent_labels + tgt_ent_labels)
            )  # form a synonym group without distinguishing ontology source
        if apply_transitivity_to_each:
            synonym_groups = self.merge_synonyms_by_transitivity(synonym_groups)
        new_section = AttrDict(
            {
                "onto_name": f"[cross-onto]: ({src_onto.owl.name}, {tgt_onto.owl.name})",
                "onto_info": f"{src_onto}\n{tgt_onto}",
                "num_synonym_groups": len(synonym_groups),
                "synonym_groups": synonym_groups,
            }
        )
        self.sections.append(new_section)
        print(
            f"Add {new_section.num_synonym_groups} synonym groups from the mappings of following ontologies:\n"
        )
        print(f"{new_section.onto_info}")
        self.create_merged_section()
        return synonym_group_pairs

    ##################################################################################
    ###                   auxiliary functions for transitivity                     ###
    ##################################################################################

    @classmethod
    def merge_synonyms_by_transitivity(cls, *synonym_group_seq: List[Set[str]]):
        """With transitivity assumed, to merge different synonym groups
        """
        label_pairs = []
        for synonym_group in synonym_group_seq:
            for synonym_set in synonym_group:
                label_pairs += itertools.product(synonym_set, synonym_set)
        merged_grouped_synonyms = cls.connected_labels(label_pairs)
        return merged_grouped_synonyms

    @staticmethod
    def connected_labels(label_pairs: List[Tuple[str, str]]) -> List[Set[str]]:
        """Build a graph for adjacency among the class labels such that
        the transitivity of synonyms is ensured

        Args:
            label_pairs (List[Tuple[str, str]]): label pairs that are synonymous

        Returns:
            List[Set[str]]: a collection of synonym sets
        """
        graph = nx.Graph()
        graph.add_edges_from(label_pairs)
        # nx.draw(G, with_labels = True)
        connected = list(nx.connected_components(graph))
        return connected

    ##################################################################################
    ###                          +ve and -ve sampling                              ###
    ##################################################################################

    @staticmethod
    def positive_sampling(synonym_groups: List[Set[str]], pos_num: Optional[int] = None):
        """Generate synonym pairs from each independent synonym group
        """
        pos_sample_pool = []
        for synonym_set in synonym_groups:
            synonym_pairs = list(itertools.product(synonym_set, synonym_set))
            pos_sample_pool += synonym_pairs
        pos_sample_pool = uniqify(pos_sample_pool)
        if (not pos_num) or (pos_num >= len(pos_sample_pool)):
            # return all the possible synonyms if no maximum limit
            return pos_sample_pool
        else:
            return random.sample(pos_sample_pool, pos_num)

    @staticmethod
    def random_negative_sampling(synonym_groups: List[Set[str]], neg_num: int):
        """Soft (random) non-synonyms are defined as label pairs from two different synonym groups
        that are randomly selected
        """
        neg_sample_pool = []
        # randomly select disjoint synonym group pairs from all
        while len(neg_sample_pool) < neg_num:
            left, right = tuple(random.sample(synonym_groups, 2))
            # randomly choose one label from a synonym group
            left_label = random.choice(list(left))
            right_label = random.choice(list(right))
            neg_sample_pool.append((left_label, right_label))
            neg_sample_pool = uniqify(neg_sample_pool)
        return neg_sample_pool

    @staticmethod
    def disjointness_negative_sampling(disjoint_synonym_groups: List[List[Set[str]]], neg_num: int):
        """Hard (disjoint) non-synonyms are defined as label pairs from two different synonym groups
        that are logically disjoint
        """
        neg_sample_pool = []
        # randomly select disjoint synonym group pairs from defined disjointness
        while len(neg_sample_pool) < neg_num:
            disjoint_group = random.choice(disjoint_synonym_groups)
            left, right = tuple(random.sample(disjoint_group, 2))
            # randomly choose one label from a synonym group
            left_label = random.choice(list(left))
            right_label = random.choice(list(right))
            neg_sample_pool.append((left_label, right_label))
            neg_sample_pool = uniqify(neg_sample_pool)
        return neg_sample_pool

    @staticmethod
    def positive_sampling_from_paired_groups(
        matched_synonym_groups: List[Tuple[Set[str], Set[str]]], pos_num: Optional[int] = None
    ):
        """Generate synonym pairs from each paired synonym group where identity synonyms are removed
        """
        pos_sample_pool = []
        for left_synonym_set, right_synonym_set in matched_synonym_groups:
            # sample cross-onto synonyms but removing identity synonyms
            synonym_pairs = [
                (l, r) for l, r in itertools.product(left_synonym_set, right_synonym_set) if l != r
            ]
            pos_sample_pool += synonym_pairs
        pos_sample_pool = uniqify(pos_sample_pool)
        if (not pos_num) or (pos_num >= len(pos_sample_pool)):
            # return all the possible synonyms if no maximum limit
            return pos_sample_pool
        else:
            return random.sample(pos_sample_pool, pos_num)

    @staticmethod
    def random_negative_sampling_from_paired_groups(
        matched_synonym_groups: List[Tuple[Set[str], Set[str]]], neg_num: int
    ):
        """Soft (random) non-synonyms are defined as label pairs from two different synonym groups
        that are randomly selected from oposite ontologies
        """
        neg_sample_pool = []
        # randomly select disjoint synonym group pairs from all
        while len(neg_sample_pool) < neg_num:
            left_class_pairs, right_class_pairs = tuple(random.sample(matched_synonym_groups, 2))
            # randomly choose one label from a synonym group
            left_label = random.choice(list(left_class_pairs[0]))  # choosing the src side
            right_label = random.choice(list(right_class_pairs[1]))  # choosing the tgt side
            neg_sample_pool.append((left_label, right_label))
            neg_sample_pool = uniqify(neg_sample_pool)
        return neg_sample_pool
