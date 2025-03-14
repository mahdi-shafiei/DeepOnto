# Copyright 2021 Yuan He. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import logging
import math
import os
from collections import defaultdict

import spacy
from anytree import NodeMixin, RenderTree
from anytree.dotexport import RenderTreeGraph
from IPython.display import Image
from org.semanticweb.owlapi.model import OWLAxiom, OWLClassExpression, OWLObject  # type: ignore
from yacs.config import CfgNode

from .ontology import Ontology

logger = logging.getLogger(__name__)

ABBREVIATION_DICT = {
    "ObjectComplementOf": "[NEG]",  # negation
    "ObjectSomeValuesFrom": "[EX.]",  # existential restriction
    "ObjectAllValuesFrom": "[ALL]",  # universal restriction
    "ObjectUnionOf": "[OR.]",  # disjunction
    "ObjectIntersectionOf": "[AND]",  # conjunction
    "ObjectPropertyChain": "[OPC]",  # object property chain
    "EquivalentClasses": "[EQV]",  # equivalence
    "SubClassOf": "[SUB]",  # subsumed by (class)
    "SuperClassOf": "[SUP]",  # subsumes (class)
    "ClassAssertion": "[CLA]",  # class assertion
    "SubObjectPropertyOf": "[SUB]",  # subsumed by (object property)
    "SuperObjectPropertyOf": "[SUP]",  #  subsumes (object property)
    "ObjectPropertyAssertion": "[OPA]",  # object property assertion
    "ObjectPropertyDomain": "[OPD]",  # object property domain
    "DataPropertyDomain": "[DPD]",  # data property domain
    "AnnotationPropertyDomain": "[APD]",  # annotation property domain
    "ObjectPropertyRange": "[OPR]",  # object property range
    "DataPropertyRange": "[DPR]",  # data property range
    "AnnotationPropertyRange": "[APR]",  # annotation property range
}

RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

# A set of common English prepositions. You can expand or modify this list as needed.
PREPOSITIONS = set(
    [
        "about",
        "above",
        "across",
        "after",
        "against",
        "along",
        "among",
        "around",
        "at",
        "before",
        "behind",
        "below",
        "beneath",
        "beside",
        "between",
        "by",
        "during",
        "for",
        "from",
        "in",
        "into",
        "like",
        "near",
        "of",
        "off",
        "on",
        "over",
        "through",
        "to",
        "under",
        "up",
        "with",
        "without",
    ]
)


class OntologyVerbaliser:
    r"""A recursive natural language verbaliser for the OWL logical expressions, e.g., [`OWLAxiom`](http://owlcs.github.io/owlapi/apidocs_5/org/semanticweb/owlapi/model/OWLAxiom.html)
    and [`OWLClassExpression`](https://owlcs.github.io/owlapi/apidocs_4/org/semanticweb/owlapi/model/OWLClassExpression.html).

    The concept patterns supported by this verbaliser are shown below:

    | **Pattern**                 | **Verbalisation** ($\mathcal{V}$)                                                                                                                                                    |
    |-----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | $A$ (atomic)                | the name ($\texttt{rdfs:label}$) of $A$  (auto-correction is optional)                                                                                                                                              |
    | $r$ (property)              | the name ($\texttt{rdfs:label}$) of $r$  (auto-correction is optional)                                                |
    | $\neg C$                    | *"not $\mathcal{V}(C)$"*                                                                                                                                                              |
    | $\exists r.C$               | *"something that $\mathcal{V}(r)$ some $\mathcal{V}(C)$"*  (the quantifier word *"some"* is optional)                                                                                                              |
    | $\forall r.C$               | *"something that $\mathcal{V}(r)$ only $\mathcal{V}(C)$"*  (the quantifier word *"only"* is optional)                                                                                                                           |
    | $C_1 \sqcap ... \sqcap C_n$ | if $C_i = \exists/\forall r.D_i$ and $C_j = \exists/\forall r.D_j$, they will be re-written into $\exists/\forall r.(D_i \sqcap D_j)$ before verbalisation; suppose after re-writing the new expression is $C_1 \sqcap ... \sqcap C_{n'}$ <p> **(a)** if **all** $C_i$s (for $i = 1, ..., n'$) are restrictions, in the form of $\exists/\forall r_i.D_i$: <br /> *"something that $\mathcal{V}(r_1)$ some/only $V(D_1)$ and ... and $\mathcal{V}(r_{n'})$ some/only $V(D_{n'})$"* <br /> **(b)** if **some** $C_i$s (for $i = m+1, ..., n'$) are restrictions, in the form of $\exists/\forall r_i.D_i$: <br /> *"$\mathcal{V}(C_{1})$ and ... and $\mathcal{V}(C_{m})$ that $\mathcal{V}(r_{m+1})$ some/only $V(D_{m+1})$ and ... and $\mathcal{V}(r_{n'})$ some/only $V(D_{n'})$"* <br /> **(c)** if **no** $C_i$ is a restriction: <br /> *"$\mathcal{V}(C_{1})$ and ... and $\mathcal{V}(C_{n'})$"* |
    | $C_1 \sqcup ... \sqcup C_n$ | similar to verbalising $C_1 \sqcap ... \sqcap C_n$ except that *"and"* is replaced by *"or"* and case **(b)** uses the same verbalisation as case **(c)**                             |
    | $r_1 \cdot r_2$ (property chain) |  $\mathcal{V}(r_1)$ something that $\mathcal{V}(r_2)$ |


    With this concept verbaliser, a range of OWL axioms are supported:

    - Class axioms for subsumption, equivalence, assertion.
    - Object property axioms for subsumption, assertion.

    The verbaliser operates at the concept level, and an additional template is needed to integrate the verbalised components of an axiom.


    !!! warning

        This verbaliser utilises spacy for POS tagging used in the auto-correction of property names.
        Automatic download of the rule-based library `en_core_web_sm` is available at the init function. However, if you
        somehow cannot find it, please manually download it using `python -m spacy download en_core_web_sm`.


    Attributes:
        onto (Ontology): An ontology whose entities and axioms are to be verbalised.
        parser (OntologySyntaxParser): A syntax parser for the string representation of an `OWLObject`.
        vocab (dict[str, list[str]]): A dictionary with `(entity_iri, entity_name)` pairs, by default
            the names are retrieved from $\texttt{rdfs:label}$.
        apply_lowercasing (bool, optional): Whether to apply lowercasing to the entity names. Defaults to `False`.
        keep_iri (bool, optional): Whether to keep the IRIs of entities without verbalising them using `self.vocab`. Defaults to `False`.
        apply_auto_correction (bool, optional): Whether to automatically apply rule-based auto-correction to entity names. Defaults to `False`.
        add_quantifier_word (bool, optional): Whether to add quantifier words ("some"/"only") as in the Manchester syntax. Defaults to `False`.
    """

    def __init__(
        self,
        onto: Ontology,
        apply_lowercasing: bool = False,
        keep_iri: bool = False,
        apply_auto_correction: bool = False,
        add_quantifier_word: bool = False,
    ):
        """Initialise an ontology verbaliser.

        Args:
            onto (Ontology): An ontology whose entities and axioms are to be verbalised.
            apply_lowercasing (bool, optional): Whether to apply lowercasing to the entity names. Defaults to `False`.
            keep_iri (bool, optional): Whether to keep the IRIs of entities without verbalising them using `self.vocab`. Defaults to `False`.
            apply_auto_correction (bool, optional): Whether to automatically apply rule-based auto-correction to entity names. Defaults to `False`.
            add_quantifier_word (bool, optional): Whether to add quantifier words ("some"/"only") as in the Manchester syntax. Defaults to `False`.
        """
        self.onto = onto
        self.parser = OntologySyntaxParser()

        # download en_core_web_sm for object property
        try:
            spacy.load("en_core_web_sm")
        except Exception:
            print("Download `en_core_web_sm` for pos tagger.")
            os.system("python -m spacy download en_core_web_sm")

        self.nlp = spacy.load("en_core_web_sm")

        # build the default vocabulary for entities
        self.apply_lowercasing_to_vocab = apply_lowercasing
        self.vocab = dict()
        for entity_type in ["Classes", "ObjectProperties", "DataProperties", "Individuals"]:
            entity_annotations, _ = self.onto.build_annotation_index(
                entity_type=entity_type, apply_lowercasing=self.apply_lowercasing_to_vocab
            )
            self.vocab.update(**entity_annotations)
        literal_or_iri = lambda k, v: list(v)[0] if v else k  # set vocab to IRI if no string available
        self.vocab = {k: literal_or_iri(k, v) for k, v in self.vocab.items()}  # only set one name for each entity

        self.keep_iri = keep_iri
        self.apply_auto_correction = apply_auto_correction
        self.add_quantifier_word = add_quantifier_word

    def update_entity_name(self, entity_iri: str, entity_name: str):
        """Update the name of an entity in `self.vocab`.

        If you want to change the name of a specific entity, you should call this
        function before applying verbalisation.
        """
        self.vocab[entity_iri] = entity_name

    def verbalise_class_expression(self, class_expression: OWLClassExpression | str | RangeNode):
        r"""Verbalise a class expression (`OWLClassExpression`) or its parsed form (in `RangeNode`).

        See currently supported types of class (or concept) expressions [here][deeponto.onto.verbalisation.OntologyVerbaliser].


        Args:
            class_expression (Union[OWLClassExpression, str, RangeNode]): A class expression to be verbalised.

        Raises:
            RuntimeError: Occurs when the class expression is not in one of the supported types.

        Returns:
            (CfgNode): A nested dictionary that presents the recursive results of verbalisation. The verbalised string
                can be accessed with the key `["verbal"]` or with the attribute `.verbal`.
        """

        if not isinstance(class_expression, RangeNode):
            parsed_class_expression = self.parser.parse(class_expression).children[0]  # skip the root node
        else:
            parsed_class_expression = class_expression

        # for a singleton IRI
        if parsed_class_expression.is_iri:
            return self._verbalise_iri(parsed_class_expression)

        if parsed_class_expression.name.startswith("NEG"):
            # negation only has one child
            cl = self.verbalise_class_expression(parsed_class_expression.children[0])
            return CfgNode({"verbal": "not " + cl.verbal, "class": cl, "type": "NEG"})

        # for existential and universal restrictions
        if parsed_class_expression.name.startswith("EX.") or parsed_class_expression.name.startswith("ALL"):
            return self._verbalise_restriction(parsed_class_expression)

        # for conjunction and disjunction
        if parsed_class_expression.name.startswith("AND") or parsed_class_expression.name.startswith("OR"):
            return self._verbalise_junction(parsed_class_expression)

        # for a property chain
        if parsed_class_expression.name.startswith("OPC"):
            return self._verbalise_property(parsed_class_expression)

        raise RuntimeError(f"Input class expression `{str(class_expression)}` is not in one of the supported types.")

    def _fix_noun_phrase(self, noun_phrase: str):
        """Rule-based auto-correction for the noun phrase."""
        # Rule 1. Remove the preposition word if it appears to be the last word of the noun phrase.
        words = noun_phrase.split(" ")
        if words[-1] in PREPOSITIONS:
            noun_phrase = " ".join(words[:-1])
        return noun_phrase

    def _fix_verb_phrase(self, verb_phrase: str):
        """Rule-based auto-correction for the verb phrase."""
        doc = self.nlp(verb_phrase)
        # Rule 1. Add "is" if the object property starts with a NOUN, ADJ, or passive VERB
        if doc[0].pos_ == "NOUN" or doc[0].pos_ == "ADJ" or (doc[0].pos_ == "VERB" and doc[0].text.endswith("ed")):
            verb_phrase = "is " + verb_phrase
        return verb_phrase

    def _verbalise_iri(self, iri_node: RangeNode, is_property: bool = False):
        """Verbalise a (parsed) named entity (class, property, or individual) that has an IRI."""
        iri = iri_node.text.lstrip("<").rstrip(">")

        try:
            verbal = self.vocab[iri] if not self.keep_iri else iri_node.text
        except KeyError:
            verbal = iri_node.text
            logger.warning(f"Use full IRI as no vocab (defaults to `rdfs:label`) found for {iri}. ")

        if self.apply_auto_correction:
            fix = self._fix_verb_phrase if is_property else self._fix_noun_phrase
            verbal = fix(verbal)
        return CfgNode({"verbal": verbal, "iri": iri, "type": "IRI"})

    def _verbalise_property(self, property_node: RangeNode):
        """Verbalise a (parsed) property expression in the form of IRI or property chain."""
        if property_node.is_iri:
            return self._verbalise_iri(property_node, is_property=True)
        else:
            properties = [self._verbalise_iri(p, is_property=True) for p in property_node.children]
            verbal = " something that ".join([p.verbal for p in properties])
            return CfgNode(
                {
                    "verbal": verbal,
                    "properties": properties,
                    "type": property_node.name[:3],
                }
            )

    def _verbalise_restriction(self, restriction_node: RangeNode, add_something: bool = True):
        """Verbalise a (parsed) class expression in the form of existential or universal restriction."""

        try:
            assert restriction_node.name.startswith("EX.") or restriction_node.name.startswith("ALL")
            assert len(restriction_node.children) == 2
        except Exception:
            raise RuntimeError("Input range node is not related to a existential or universal restriction statement.")

        quantifier_word = "some" if restriction_node.name.startswith("EX.") else "only"

        object_property = restriction_node.children[0]
        # assert object_property.is_iri
        object_property = self._verbalise_property(object_property)

        class_expression = restriction_node.children[1]
        class_expression = self.verbalise_class_expression(class_expression.text)

        # adding quantifier word or not
        if self.add_quantifier_word:
            verbal = f"{object_property.verbal} {quantifier_word} {class_expression.verbal}"
        else:
            verbal = f"{object_property.verbal} {class_expression.verbal}"

        verbal = verbal.lstrip()
        if add_something:
            verbal = "something that " + verbal

        return CfgNode(
            {
                "verbal": verbal,
                "property": object_property,
                "class": class_expression,
                "type": restriction_node.name[:3],
            }
        )

    def _verbalise_junction(self, junction_node: RangeNode):
        """Verbalise a (parsed) class expression in the form of conjunction or disjunction."""

        try:
            assert junction_node.name.startswith("AND") or junction_node.name.startswith("OR.")
        except Exception:
            raise RuntimeError("Input range node is not related to a conjunction or disjunction statement.")

        junction_word = "and" if junction_node.name.startswith("AND") else "or"

        # collect restriction nodes for merging
        existential_restriction_children = defaultdict(list)
        universal_restriction_children = defaultdict(list)
        other_children = []
        for child in junction_node.children:
            if child.name.startswith("EX."):
                child = self._verbalise_restriction(child, add_something=False)
                existential_restriction_children[child.property.verbal].append(child)
            elif child.name.startswith("ALL"):
                child = self._verbalise_restriction(child, add_something=False)
                universal_restriction_children[child.property.verbal].append(child)
            else:
                other_children.append(self.verbalise_class_expression(child))

        merged_children = []
        for v in list(existential_restriction_children.values()) + list(universal_restriction_children.values()):
            # restriction = v[0].type
            if len(v) > 1:
                merged_child = CfgNode(dict())
                merged_child.update(v[0])  # initialised with the first one
                merged_child["class"] = CfgNode(
                    {"verbal": v[0]["class"].verbal, "classes": [v[0]["class"]], "type": junction_node.name[:3]}
                )

                for i in range(1, len(v)):
                    # v 0.5.2 fix for len(v) > 1 case
                    merged_child.verbal += (
                        f" {junction_word} " + v[i]["class"].verbal
                    )  # update grouped concepts with property
                    merged_child["class"].verbal += (
                        f" {junction_word} " + v[i]["class"].verbal
                    )  # update grouped concepts
                    merged_child["class"].classes.append(v[i]["class"])
                merged_children.append(merged_child)
                # print(merged_children)
            else:
                merged_children.append(v[0])

        results = CfgNode(
            {
                "verbal": "",
                "classes": other_children + merged_children,
                "type": junction_node.name[:3],
            }
        )

        # add the preceeding "something that" if there are only restrictions
        if not other_children:
            results.verbal += " something that " + f" {junction_word} ".join(c.verbal for c in merged_children)
            results.verbal.lstrip()
        else:
            results.verbal += f" {junction_word} ".join(c.verbal for c in other_children)
            if merged_children:
                if junction_word == "and":
                    # sea food and non-vergetarian product that derives from shark and goldfish
                    results.verbal += " that " + f" {junction_word} ".join(c.verbal for c in merged_children)
                elif junction_word == "or":
                    # sea food or non-vergetarian product or something that derives from shark or goldfish
                    results.verbal += " or something that " + f" {junction_word} ".join(
                        c.verbal for c in merged_children
                    )

        return results

    def _axiom_input_check(self, axiom: OWLAxiom, *required_axiom_types):
        axiom_type = self.onto.get_axiom_type(axiom)
        assert (
            axiom_type in required_axiom_types
        ), f"Input axiom type `{axiom_type}` is not in {list(required_axiom_types)}."

    def verbalise_class_subsumption_axiom(self, class_subsumption_axiom: OWLAxiom):
        r"""Verbalise a class subsumption axiom.

        The subsumption axiom can have two forms:

        - $C_{sub} \sqsubseteq C_{super}$, the `SubClassOf` axiom;
        - $C_{super} \sqsupseteq C_{sub}$, the `SuperClassOf` axiom.

        Args:
            class_subsumption_axiom (OWLAxiom): Then class subsumption axiom to be verbalised.

        Returns:
            (Tuple[CfgNode, CfgNode]): The verbalised sub-concept $\mathcal{V}(C_{sub})$ and super-concept $\mathcal{V}(C_{super})$ (order matters).
        """

        # input check
        self._axiom_input_check(class_subsumption_axiom, "SubClassOf", "SuperClassOf")

        parsed_subsumption_axiom = self.parser.parse(class_subsumption_axiom).children[0]  # skip the root node
        if str(class_subsumption_axiom).startswith("SubClassOf"):
            parsed_sub_class, parsed_super_class = parsed_subsumption_axiom.children
        elif str(class_subsumption_axiom).startswith("SuperClassOf"):
            parsed_super_class, parsed_sub_class = parsed_subsumption_axiom.children

        verbalised_sub_class = self.verbalise_class_expression(parsed_sub_class)
        verbalised_super_class = self.verbalise_class_expression(parsed_super_class)
        return verbalised_sub_class, verbalised_super_class

    def verbalise_class_equivalence_axiom(self, class_equivalence_axiom: OWLAxiom):
        r"""Verbalise a class equivalence axiom.

        The equivalence axiom has the form $C \equiv D$.

        Args:
            class_equivalence_axiom (OWLAxiom): The class equivalence axiom to be verbalised.

        Returns:
            (Tuple[CfgNode, CfgNode]): The verbalised concept $\mathcal{V}(C)$ and its equivalent concept $\mathcal{V}(D)$ (order matters).
        """

        # input check
        self._axiom_input_check(class_equivalence_axiom, "EquivalentClasses")

        parsed_equivalence_axiom = self.parser.parse(class_equivalence_axiom).children[0]  # skip the root node
        parsed_class_left, parsed_class_right = parsed_equivalence_axiom.children

        verbalised_left_class = self.verbalise_class_expression(parsed_class_left)
        verbalised_right_class = self.verbalise_class_expression(parsed_class_right)
        return verbalised_left_class, verbalised_right_class

    def verbalise_class_assertion_axiom(self, class_assertion_axiom: OWLAxiom):
        r"""Verbalise a class assertion axiom.

        The class assertion axiom has the form $C(x)$.

        Args:
            class_assertion_axiom (OWLAxiom): The class assertion axiom to be verbalised.

        Returns:
            (Tuple[CfgNode, CfgNode]): The verbalised class $\mathcal{V}(C)$ and individual $\mathcal{V}(x)$ (order matters).
        """

        # input check
        self._axiom_input_check(class_assertion_axiom, "ClassAssertion")

        parsed_equivalence_axiom = self.parser.parse(class_assertion_axiom).children[0]  # skip the root node
        parsed_class, parsed_individual = parsed_equivalence_axiom.children

        verbalised_class = self.verbalise_class_expression(parsed_class)
        verbalised_individual = self._verbalise_iri(parsed_individual)
        return verbalised_class, verbalised_individual

    def verbalise_object_property_subsumption_axiom(self, object_property_subsumption_axiom: OWLAxiom):
        r"""Verbalise an object property subsumption axiom.

        The subsumption axiom can have two forms:

        - $r_{sub} \sqsubseteq r_{super}$, the `SubObjectPropertyOf` axiom;
        - $r_{super} \sqsupseteq r_{sub}$, the `SuperObjectPropertyOf` axiom.

        Args:
            object_property_subsumption_axiom (OWLAxiom): The object property subsumption axiom to be verbalised.

        Returns:
            (Tuple[CfgNode, CfgNode]): The verbalised sub-property $\mathcal{V}(r_{sub})$ and super-property $\mathcal{V}(r_{super})$ (order matters).
        """

        # input check
        self._axiom_input_check(
            object_property_subsumption_axiom,
            "SubObjectPropertyOf",
            "SuperObjectPropertyOf",
            "SubPropertyChainOf",
            "SuperPropertyChainOf",
        )

        parsed_subsumption_axiom = self.parser.parse(object_property_subsumption_axiom).children[
            0
        ]  # skip the root node
        if str(object_property_subsumption_axiom).startswith("SubObjectPropertyOf"):
            parsed_sub_property, parsed_super_property = parsed_subsumption_axiom.children
        elif str(object_property_subsumption_axiom).startswith("SuperObjectPropertyOf"):
            parsed_super_property, parsed_sub_property = parsed_subsumption_axiom.children

        verbalised_sub_property = self._verbalise_property(parsed_sub_property)
        verbalised_super_property = self._verbalise_property(parsed_super_property)
        return verbalised_sub_property, verbalised_super_property

    def verbalise_object_property_assertion_axiom(self, object_property_assertion_axiom: OWLAxiom):
        r"""Verbalise an object property assertion axiom.

        The object property assertion axiom has the form $r(x, y)$.

        Args:
            object_property_assertion_axiom (OWLAxiom): The object property assertion axiom to be verbalised.

        Returns:
            (Tuple[CfgNode, CfgNode]): The verbalised object property $\mathcal{V}(r)$ and two individuals $\mathcal{V}(x)$ and $\mathcal{V}(y)$ (order matters).
        """

        # input check
        self._axiom_input_check(object_property_assertion_axiom, "ObjectPropertyAssertion")

        # skip the root node
        parsed_object_property_assertion_axiom = self.parser.parse(object_property_assertion_axiom).children[0]
        parsed_obj_prop, parsed_indiv_x, parsed_indiv_y = parsed_object_property_assertion_axiom.children

        verbalised_object_property = self._verbalise_iri(parsed_obj_prop, is_property=True)
        verbalised_individual_x = self._verbalise_iri(parsed_indiv_x)
        verbalised_individual_y = self._verbalise_iri(parsed_indiv_y)
        return verbalised_object_property, verbalised_individual_x, verbalised_individual_y

    def verbalise_object_property_domain_axiom(self, object_property_domain_axiom: OWLAxiom):
        r"""Verbalise an object property domain axiom.

        The domain of a property $r: X \rightarrow Y$ specifies the concept expression $X$ of its subject.

        Args:
            object_property_domain_axiom (OWLAxiom): The object property domain axiom to be verbalised.

        Returns:
            (Tuple[CfgNode, CfgNode]): The verbalised object property $\mathcal{V}(r)$ and its domain $\mathcal{V}(X)$ (order matters).
        """

        # input check
        self._axiom_input_check(object_property_domain_axiom, "ObjectPropertyDomain")

        # skip the root node
        parsed_object_property_domain_axiom = self.parser.parse(object_property_domain_axiom).children[0]
        parsed_obj_prop, parsed_obj_prop_domain = parsed_object_property_domain_axiom.children

        verbalised_object_property = self._verbalise_iri(parsed_obj_prop, is_property=True)
        verbalised_object_property_domain = self.verbalise_class_expression(parsed_obj_prop_domain)

        return verbalised_object_property, verbalised_object_property_domain

    def verbalise_object_property_range_axiom(self, object_property_range_axiom: OWLAxiom):
        r"""Verbalise an object property range axiom.

        The range of a property $r: X \rightarrow Y$ specifies the concept expression $Y$ of its object.

        Args:
            object_property_range_axiom (OWLAxiom): The object property range axiom to be verbalised.

        Returns:
            (Tuple[CfgNode, CfgNode]): The verbalised object property $\mathcal{V}(r)$ and its range $\mathcal{V}(Y)$ (order matters).
        """

        # input check
        self._axiom_input_check(object_property_range_axiom, "ObjectPropertyRange")

        # skip the root node
        parsed_object_property_range_axiom = self.parser.parse(object_property_range_axiom).children[0]
        parsed_obj_prop, parsed_obj_prop_range = parsed_object_property_range_axiom.children

        verbalised_object_property = self._verbalise_iri(parsed_obj_prop, is_property=True)
        verbalised_object_property_range = self.verbalise_class_expression(parsed_obj_prop_range)

        return verbalised_object_property, verbalised_object_property_range


class OntologySyntaxParser:
    r"""A syntax parser for the OWL logical expressions, e.g., [`OWLAxiom`](http://owlcs.github.io/owlapi/apidocs_5/org/semanticweb/owlapi/model/OWLAxiom.html)
    and [`OWLClassExpression`](https://owlcs.github.io/owlapi/apidocs_4/org/semanticweb/owlapi/model/OWLClassExpression.html).

    It makes use of the string representation (based on Manchester Syntax) defined in the OWLAPI. In Python,
    such string can be accessed by simply using `#!python str(some_owl_object)`.

    To keep the Java import in the main [`Ontology`][deeponto.onto.Ontology] class,
    this parser does not deal with `OWLAxiom` directly but instead its **string representation**.

    Due to the `OWLObject` syntax, this parser relies on two components:

    1. Parentheses matching;
    2. Tree construction ([`RangeNode`][deeponto.onto.verbalisation.RangeNode]).

    As a result, it will return a [`RangeNode`][deeponto.onto.verbalisation.RangeNode] that
    specifies the sub-formulas (and their respective **positions in the string representation**)
    in a tree structure.

    Examples:

        Suppose the input is an `OWLAxiom` that has the string representation:

        ```python
        >>> str(owl_axiom)
        >>> 'EquivalentClasses(<http://purl.obolibrary.org/obo/FOODON_00001707> ObjectIntersectionOf(<http://purl.obolibrary.org/obo/FOODON_00002044> ObjectSomeValuesFrom(<http://purl.obolibrary.org/obo/RO_0001000> <http://purl.obolibrary.org/obo/FOODON_03412116>)) )'
        ```

        This corresponds to the following logical expression:

        $$
        CephalopodFoodProduct \equiv MolluskFoodProduct \sqcap \exists derivesFrom.Cephalopod
        $$

        After apply the parser, a [`RangeNode`][deeponto.onto.verbalisation.RangeNode] will be returned which can be rentered as:

        ```python
        axiom_parser = OntologySyntaxParser()
        print(axiom_parser.parse(str(owl_axiom)).render_tree())
        ```

        `#!console Output:`
        :   &#32;
            ```python
            Root@[0:inf]
            └── EQV@[0:212]
                ├── FOODON_00001707@[6:54]
                └── AND@[55:210]
                    ├── FOODON_00002044@[61:109]
                    └── EX.@[110:209]
                        ├── RO_0001000@[116:159]
                        └── FOODON_03412116@[160:208]
            ```

        Or, if `graphviz` (installed by e.g., `sudo apt install graphviz`) is available,
        you can visualise the tree as an image by:

        ```python
        axiom_parser.parse(str(owl_axiom)).render_image()
        ```

        `#!console Output:`

        <p align="center">
            <img alt="range_node" src="../../../assets/example_range_node.png" style="padding: 30px 50px">
        </p>


        The name for each node has the form `{node_type}@[{start}:{end}]`, which means a node of the type `{node_type}` is
        located at the range `[{start}:{end}]` in the **abbreviated** expression  (see [`abbreviate_owl_expression`][deeponto.onto.verbalisation.OntologySyntaxParser.abbreviate_owl_expression]
        below).

        The leaf nodes are IRIs and they are represented by the last segment (split by `"/"`) of the whole IRI.

        Child nodes can be accessed by `.children`, the string representation of the sub-formula in this node can be
        accessed by `.text`. For example:

        ```python
        parser.parse(str(owl_axiom)).children[0].children[1].text
        ```

        `#!console Output:`
        :   &#32;
            ```python
            '[AND](<http://purl.obolibrary.org/obo/FOODON_00002044> [EX.](<http://purl.obolibrary.org/obo/RO_0001000> <http://purl.obolibrary.org/obo/FOODON_03412116>))'
            ```

    """

    def __init__(self):
        pass

    def abbreviate_owl_expression(self, owl_expression: str):
        r"""Abbreviate the string representations of logical operators to a
        fixed length (easier for parsing).

        The abbreviations are specified at `deeponto.onto.verbalisation.ABBREVIATION_DICT`.

        Args:
            owl_expression (str): The string representation of an `OWLObject`.

        Returns:
            (str): The modified string representation of this `OWLObject` where the logical operators are abbreviated.
        """
        for k, v in ABBREVIATION_DICT.items():
            owl_expression = owl_expression.replace(k, v)
        return owl_expression

    def parse(self, owl_expression: str | OWLObject) -> RangeNode:
        r"""Parse an `OWLAxiom` into a [`RangeNode`][deeponto.onto.verbalisation.RangeNode].

        This is the main entry for using the parser, which relies on the [`parse_by_parentheses`][deeponto.onto.verbalisation.OntologySyntaxParser.parse_by_parentheses]
        method below.

        Args:
            owl_expression (Union[str, OWLObject]): The string representation of an `OWLObject` or the `OWLObject` itself.

        Returns:
            (RangeNode): A parsed syntactic tree given what parentheses to be matched.
        """
        if not isinstance(owl_expression, str):
            owl_expression = str(owl_expression)
        owl_expression = self.abbreviate_owl_expression(owl_expression)
        # print("To parse the following (transformed) axiom text:\n", owl_expression)
        # parse complex patterns first
        cur_parsed = self.parse_by_parentheses(owl_expression)
        # parse the IRI patterns latter
        return self.parse_by_parentheses(owl_expression, cur_parsed, for_iri=True)

    @classmethod
    def parse_by_parentheses(
        cls, owl_expression: str, already_parsed: RangeNode = None, for_iri: bool = False
    ) -> RangeNode:
        r"""Parse an `OWLAxiom` based on parentheses matching into a [`RangeNode`][deeponto.onto.verbalisation.RangeNode].

        This function needs to be applied twice to get a fully parsed [`RangeNode`][deeponto.onto.verbalisation.RangeNode] because IRIs have
        a different parenthesis pattern.

        Args:
            owl_expression (str): The string representation of an `OWLObject`.
            already_parsed (RangeNode, optional): A partially parsed [`RangeNode`][deeponto.onto.verbalisation.RangeNode] to continue with. Defaults to `None`.
            for_iri (bool, optional): Parentheses are by default `()` but will be changed to `<>` for IRIs. Defaults to `False`.

        Raises:
            RuntimeError: Raised when the input axiom text is nor properly formatted.

        Returns:
            (RangeNode): A parsed syntactic tree given what parentheses to be matched.
        """
        if not already_parsed:
            # a root node that covers the entire sentence
            parsed = RangeNode(0, math.inf, name="Root", text=owl_expression, is_iri=False)
        else:
            parsed = already_parsed
        stack = []
        left_par = "("
        right_par = ")"
        if for_iri:
            left_par = "<"
            right_par = ">"

        for i, c in enumerate(owl_expression):
            if c == left_par:
                stack.append(i)
            if c == right_par:
                try:
                    start = stack.pop()
                    end = i
                    if not for_iri:
                        # the first character is actually "["
                        real_start = start - 5
                        axiom_type = owl_expression[real_start + 1 : start - 1]
                        node = RangeNode(
                            real_start,
                            end + 1,
                            name=f"{axiom_type}",
                            text=owl_expression[real_start : end + 1],
                            is_iri=False,
                        )
                        parsed.insert_child(node)
                    else:
                        # no preceding characters for just atomic class (IRI)
                        abbr_iri = owl_expression[start : end + 1].split("/")[-1].rstrip(">")
                        node = RangeNode(
                            start, end + 1, name=abbr_iri, text=owl_expression[start : end + 1], is_iri=True
                        )
                        parsed.insert_child(node)
                except IndexError:
                    print("Too many closing parentheses")

        if stack:  # check if stack is empty afterwards
            raise RuntimeError("Too many opening parentheses")

        return parsed


class RangeNode(NodeMixin):
    r"""A tree implementation for ranges (without partial overlap).

    - Parent node's range fully covers child node's range, e.g., `[1, 10]` is a parent of `[2, 5]`.
    - Partial overlap between ranges are not allowed, e.g., `[2, 4]` and `[3, 5]` cannot appear in the same `RangeNodeTree`.
    - Non-overlap ranges are on different branches (irrelevant).
    - Child nodes are ordered according to their relative positions.
    """

    def __init__(self, start, end, name=None, **kwargs):
        if start >= end:
            raise RuntimeError("invalid start and end positions ...")
        self.start = start
        self.end = end
        self.name = "Root" if not name else name
        self.name = f"{self.name}@[{self.start}:{self.end}]"  # add start and ent to the name
        for k, v in kwargs.items():
            setattr(self, k, v)
        super().__init__()

    # def __eq__(self, other: RangeNode):
    #     """Two ranges are equal if they have the same `start` and `end`.
    #     """
    #     return self.start == other.start and self.end == other.end

    def __gt__(self, other: RangeNode):
        r"""Compare two ranges if they have a different `start` and/or a different `end`.

        - $R_1 \lt R_2$: if range $R_1$ is completely contained in range $R_2$, and $R_1 \neq R_2$.
        - $R_1 \gt R_2$: if range $R_2$ is completely contained in range $R_1$,  and $R_1 \neq R_2$.
        - `"irrelevant"`: if range $R_1$ and range $R_2$ have no overlap.

        !!! warning

            Partial overlap is not allowed.
        """
        # ranges inside
        if self.start <= other.start and other.end <= self.end:
            return True

        # ranges outside
        if other.start <= self.start and self.end <= other.end:
            return False

        if other.end < self.start or self.end < other.start:
            return "irrelevant"

        raise RuntimeError("Compared ranges have a partial overlap.")

    @staticmethod
    def sort_by_start(nodes: list[RangeNode]):
        """A sorting function that sorts the nodes by their starting positions."""
        temp = {sib: sib.start for sib in nodes}
        return list(dict(sorted(temp.items(), key=lambda item: item[1])).keys())

    def insert_child(self, node: RangeNode):
        r"""Inserting a child [`RangeNode`][deeponto.onto.verbalisation.RangeNode].

        Child nodes have a smaller (inclusive) range, e.g., `[2, 5]` is a child of `[1, 6]`.
        """
        if node > self:
            raise RuntimeError("invalid child node")
        if node.start == self.start and node.end == self.end:
            # duplicated node
            return
        # print(self.children)
        if self.children:
            inserted = False
            for ch in self.children:
                if (node < ch) is True:
                    # print("further down")
                    ch.insert_child(node)
                    inserted = True
                    break
                elif (node > ch) is True:
                    # print("insert in between")
                    ch.parent = node
                    # NOTE: should not break here as it could be parent of multiple children !
                    # break
                # NOTE: the equal case is when two nodes are exactly the same, no operation needed
            if not inserted:
                self.children = list(self.children) + [node]
                self.children = self.sort_by_start(self.children)
        else:
            node.parent = self
            self.children = [node]

    def __repr__(self):
        return f"{self.name}"

    def render_tree(self):
        """Render the whole tree."""
        return RenderTree(self)

    def render_image(self):
        """Calling this function will generate a temporary `range_node.png` file
        which will be displayed.

        To make this visualisation work, you need to install `graphviz` by, e.g.,

        ```bash
        sudo apt install graphviz
        ```
        """
        RenderTreeGraph(self).to_picture("range_node.png")
        return Image("range_node.png")
