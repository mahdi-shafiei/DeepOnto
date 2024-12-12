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

from .normalisation import OntologyNormaliser
from .ontology import Ontology, OntologyReasoner
from .projection import OntologyProjector
from .pruning import OntologyPruner
from .taxonomy import OntologyTaxonomy, Taxonomy, TaxonomyNegativeSampler, WordnetTaxonomy
from .verbalisation import OntologySyntaxParser, OntologyVerbaliser

__all__ = [
    "Ontology",
    "OntologyReasoner",
    "OntologyPruner",
    "OntologyVerbaliser",
    "OntologySyntaxParser",
    "OntologyProjector",
    "OntologyNormaliser",
    "Taxonomy",
    "OntologyTaxonomy",
    "WordnetTaxonomy",
    "TaxonomyNegativeSampler",
]
