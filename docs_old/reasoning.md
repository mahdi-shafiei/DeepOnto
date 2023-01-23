<!---
Copyright 2021 Yuan He (KRR-Oxford). All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Ontology Reasoning

## Use OWLAPI Reasoner in Python

DeepOnto now supports ontology reasoning modules extended from OWLAPI. There are many helpful methods such as getting the inferred super/sub-classes of an ontology concept or property, checking disjointness, subsumption relationship, common descendants an so on. Users can take these methods as examples and freely implement their own useful functions.

There are other helpful methods for checking disjointness, subsumption relationship, common descendants, and so on. Check the source code for more information.

```python
from deeponto.onto.logic.reasoner import OWLReasoner

# initialise the ontology reasoner
reasoner = OWLReasoner("doid.owl")

# getting an OWLObject (class or property) instance from its IRI
owl_object = reasoner.getOWLObjectFromIRI("http://purl.obolibrary.org/obo/DOID_0040002")

# getting IRIs of the inferred super-classes of the owl_object
# set direct=True if only direct super-classes are required 
supers = reasoner.super_entities_of(owl_object, direct=False)

# getting IRIs of the inferred sub-classes of the owl_object
# set direct=True if only direct sub-classes are required 
subs = reasoner.sub_entities_of(owl_object, direct=False)

# getting another OWLObject (class or property) instance
owl_object2 = reasoner.getOWLObjectFromIRI("http://purl.obolibrary.org/obo/DOID_0040001")

# check disjointness
reasoner.check_disjoint(owl_object, owl_object2)

# check subsumption (the first argument is the sub-class)
reasoner.check_subsumption(owl_object, owl_object2)

# check any common descendants
reasoner.check_common_descendants(owl_object, owl_object2)

```

