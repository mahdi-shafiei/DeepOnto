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

<p align="center">
  <a href="https://krr-oxford.github.io/DeepOnto/">
    <img alt="deeponto" src="https://raw.githubusercontent.com/KRR-Oxford/DeepOnto/main/docs/images/icon.svg">
  </a>
</p>

<p align="center">
    <a href="https://github.com/KRR-Oxford/DeepOnto/blob/main/LICENSE">
        <img alt="license" src="https://img.shields.io/github/license/KRR-Oxford/DeepOnto">
    </a>
    <a href="https://krr-oxford.github.io/DeepOnto/">
        <img alt="docs" src="https://img.shields.io/badge/website-online-informational">
    </a>
    <a href="https://pypi.org/project/deeponto/">
        <img alt="pypi" src="https://img.shields.io/pypi/v/deeponto">
    </a>
    <a href="https://github.com/KRR-Oxford/DeepOnto">
        <img alt="stars" src="https://img.shields.io/github/stars/KRR-Oxford/DeepOnto">
    </a>
</p>

<h4 align="center">
    <p>
        <a href="https://krr-oxford.github.io/DeepOnto/">Docs</a> |
        <a href="https://github.com/KRR-Oxford/DeepOnto">GitHub</a> |
        <a href="https://arxiv.org/abs/2307.03067">arXiv</a> |
        <a href="https://content.iospress.com/articles/semantic-web/sw243568">Paper</a> 
    </p>
</h4>

<h3 align="center">
  <p>A package for ontology engineering with deep learning.</p> 
</h3>


## About

$\textsf{DeepOnto}$ aims to provide building blocks for implementing deep learning models, constructing resources, and conducting evaluation for various ontology engineering purposes.

- **Documentation**: *<https://krr-oxford.github.io/DeepOnto/>*.
- **Github Repository**: *<https://github.com/KRR-Oxford/DeepOnto>*. 
- **PyPI**: *<https://pypi.org/project/deeponto/>*. 


Check the complete [changelog](https://krr-oxford.github.io/DeepOnto/changelog/) and [FAQs](https://krr-oxford.github.io/DeepOnto/faqs/). 


## Installation

### OWLAPI

$\textsf{DeepOnto}$ relies on [OWLAPI](http://owlapi.sourceforge.net/) version 4.5.22 (written in Java) for ontologies. 

We follow what has been implemented in [mOWL](https://mowl.readthedocs.io/en/latest/index.html) that uses [JPype](https://jpype.readthedocs.io/en/latest/) to bridge Python and Java Virtual Machine (JVM). Please check JPype's [installation page](https://jpype.readthedocs.io/en/latest/install.html#) for successful JVM initialisation.


### Pytorch

$\textsf{DeepOnto}$ relies on [Pytorch](https://pytorch.org/) for deep learning framework.

We recommend installing Pytorch prior to installing $\textsf{DeepOnto}$ following the commands listed on the [Pytorch webpage](https://pytorch.org/). Notice that users can choose either GPU (with CUDA) or CPU version of Pytorch.

In case the most recent Pytorch version causes any incompatibility issues, use the following command (with `CUDA 11.6`) known to work:

```bash
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu116
```

Basic usage of $\textsf{DeepOnto}$ does not rely on GPUs, but for efficient deep learning model training, please make sure `torch.cuda.is_available()` returns `True`.

### Install from PyPI

Other dependencies are specified in `setup.cfg` and `requirements.txt` which are supposed to be installed along with `deeponto`.

```bash
# requiring Python>=3.8
pip install deeponto
```

We have been informed that `openprompt` has a conflict with several other packages that can be hardly addressed on MacOS with M1, so we now set it as an optional dependency. However, it is main dependency of the OntoLAMA code at `deeponto.complete.ontolama`. To use OntoLAMA, please install `openprompt` separately, or use the following command to install $\textsf{DeepOnto}$:

```bash
pip install deeponto[ontolama]
```

### Install from Git Repository

To install the latest, probably unreleased version of deeponto, you can directly install from the repository. 

```bash
pip install git+https://github.com/KRR-Oxford/DeepOnto.git
```

## Main Features

<p align="center">
  <img alt="deeponto" src="https://raw.githubusercontent.com/KRR-Oxford/DeepOnto/main/docs/images/deeponto.svg" width=90%">
  <p align="center">Figure: Illustration of DeepOnto's architecture.</p>
</p>

### Ontology Processing

The base class of $\textsf{DeepOnto}$ is [`Ontology`][deeponto.onto.Ontology], which serves as the main entry point for introducing the OWLAPI's features, such as accessing ontology entities, querying for ancestor/descendent (and parent/child) concepts, deleting entities, modifying axioms, and retrieving annotations. See quick usage at [load an ontology](https://krr-oxford.github.io/DeepOnto/ontology/). Along with these basic functionalities, several essential sub-modules are built to enhance the core module, including the following:

- **Ontology Reasoning** ([`OntologyReasoner`][deeponto.onto.OntologyReasoner]): Each instance of $\textsf{DeepOnto}$ has a reasoner as its attribute. It is used for conducting reasoning activities, such as obtaining inferred subsumers and subsumees, as well as checking entailment and consistency. 

- **Ontology Pruning** ([`OntologyPruner`][deeponto.onto.OntologyPruner]): This sub-module aims to incorporate pruning algorithms for extracting a sub-ontology from an input ontology. We currently implement the one proposed in [2], which introduces subsumption axioms between the asserted (atomic or complex) parents and children of the class targeted for removal.

- **Ontology Verbalisation** ([`OntologyVerbaliser`][deeponto.onto.OntologyVerbaliser]): The recursive concept verbaliser proposed in [4] is implemented here, which can automatically transform a complex logical expression into a textual sentence based on entity names or labels available in the ontology. See [verbalising ontology concepts](https://krr-oxford.github.io/DeepOnto/verbaliser).

- **Ontology Projection** ([`OntologyProjector`][deeponto.onto.OntologyProjector]): The projection algorithm adopted in the OWL2Vec* ontology embeddings is implemented here, which is to transform an ontology's TBox into a set of RDF triples. The relevant code is modified from the mOWL library.

- **Ontology Normalisation** ([`OntologyNormaliser`][deeponto.onto.OntologyNormaliser]): The implemented $\mathcal{EL}$ normalisation is also modified from the mOWL library, which is used to transform TBox axioms into normalised forms to support, e.g., geometric ontology embeddings.

- **Ontology Taxonomy** ([`OntologyTaxonomy`][deeponto.onto.OntologyTaxonomy]): The taxonomy extracted from an ontology is a directed acyclic graph for the subsumption hierarchy, which is often used to support graph-based deep learning applications.


### Tools and Resources

Individual tools and resources are implemented based on the core ontology processing module. Currently, $\textsf{DeepOnto}$ supports the following:

- **BERTMap** [1] is a BERT-based ontology matching (OM) system originally developed in [repo](https://github.com/KRR-Oxford/BERTMap) but is now maintained in $\textsf{DeepOnto}$. See [Ontology Matching with BERTMap & BERTMapLt](https://krr-oxford.github.io/DeepOnto/bertmap/).

- **Bio-ML** [2] is an OM resource that has been used in the [Bio-ML track of the OAEI](https://www.cs.ox.ac.uk/isg/projects/ConCur/oaei/). See [Bio-ML: A Comprehensive Documentation](https://krr-oxford.github.io/DeepOnto/bio-ml/). 

- **BERTSubs** [3] is a system for ontology subsumption prediction. We have transformed its original [experimental code](https://gitlab.com/chen00217/bert_subsumption) into this project. See [Subsumption Inference with BERTSubs](https://krr-oxford.github.io/DeepOnto/bertsubs/).

- **OntoLAMA** [4] is an evaluation of language model for ontology subsumption inference. See [OntoLAMA: Dataset Overview & Usage Guide](https://krr-oxford.github.io/DeepOnto/ontolama) for the use of the datasets and the prompt-based probing approach.

- **HiT (External)** [6] is a hierarchy embedding model derived from re-training BERT-like models in hyperbolic space. See [HiT Models on Huggingface Hub](https://huggingface.co/Hierarchy-Transformers) for options and usage.


## License

!!! license "License"

    Copyright 2021-2023 Yuan He.
    Copyright 2023 Yuan He, Jiaoyan Chen.
    All rights reserved.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at *<http://www.apache.org/licenses/LICENSE-2.0>*

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

## Citation

Our system papaer for $\textsf{DeepOnto}$ is available at [arxiv](https://arxiv.org/abs/2307.03067) and [ios press](https://content.iospress.com/articles/semantic-web/sw243568).

*Yuan He, Jiaoyan Chen, Hang Dong, Ian Horrocks, Carlo Allocca, Taehun Kim, and Brahmananda Sapkota.* **DeepOnto: A Python Package for Ontology Engineering with Deep Learning.** Semantic Web, vol. 15, no. 5, pp. 1991-2004, 2024.

!!! credit "Citation"

    ```
    @article{he2024deeponto,
      author = {He, Yuan and Chen, Jiaoyan and Dong, Hang and Horrocks, Ian and Allocca, Carlo and Kim, Taehun and Sapkota, Brahmananda},
      journal = {Semantic Web},
      number = {5},
      pages = {1991--2004},
      title = {DeepOnto: A Python package for ontology engineering with deep learning},
      volume = {15},
      year = {2024}
    }
    ```

## Relevant Publications

- [1] *Yuan He‚ Jiaoyan Chen‚ Denvar Antonyrajah and Ian Horrocks.* **BERTMap: A BERT−Based Ontology Alignment System**. In Proceedings of 36th AAAI Conference on Artificial Intelligence (AAAI-2022). /[arxiv](https://arxiv.org/abs/2112.02682)/ /[aaai](https://ojs.aaai.org/index.php/AAAI/article/view/20510)/  <a name="bertmap_paper"></a>
- [2] *Yuan He‚ Jiaoyan Chen‚ Hang Dong, Ernesto Jiménez-Ruiz, Ali Hadian and Ian Horrocks.* **Machine Learning-Friendly Biomedical Datasets for Equivalence and Subsumption Ontology Matching**. The 21st International Semantic Web Conference (ISWC-2022, **Best Resource Paper Candidate**). /[arxiv](https://arxiv.org/abs/2205.03447)/ /[iswc](https://link.springer.com/chapter/10.1007/978-3-031-19433-7_33)/  <a name="bioml_paper"></a>
- [3] *Jiaoyan Chen, Yuan He, Yuxia Geng, Ernesto Jiménez-Ruiz, Hang Dong and Ian Horrocks.* **Contextual Semantic Embeddings for Ontology Subsumption Prediction**. World Wide Web Journal （WWWJ-2023). /[arxiv](https://arxiv.org/abs/2202.09791)/ /[wwwj](https://link.springer.com/article/10.1007/s11280-023-01169-9)/  <a name="bertsubs_paper"></a>
- [4] *Yuan He‚ Jiaoyan Chen, Ernesto Jiménez-Ruiz, Hang Dong and Ian Horrocks.* **Language Model Analysis for Ontology Subsumption Inference**. Findings of the Association for Computational Linguistics (ACL-2023). /[arxiv](https://arxiv.org/abs/2302.06761)/ /[acl](https://aclanthology.org/2023.findings-acl.213/)/ <a name="ontolama_paper"></a>
- [5] *Yuan He, Jiaoyan Chen, Hang Dong, and Ian Horrocks.* **Exploring Large Language Models for Ontology Alignment**. The 22nd International Semantic Web Conference (ISWC-2023 Posters & Demos). /[arxiv](https://arxiv.org/abs/2309.07172)/ /[iswc](https://hozo.jp/ISWC2023_PD-Industry-proc/ISWC2023_paper_427.pdf)/ <a name="llmap_paper"></a>
- [6] *Yuan He, Zhangdie Yuan, Jiaoyan Chen, and Ian Horrocks.* **Language Models as Hierarchy Encoders**. Advances in Neural Information Processing Systems (NeurIPS 2024). /[arxiv](https://arxiv.org/abs/2401.11374)/ /[neurips](https://nips.cc/virtual/2024/poster/95913)/ <a name="hit_paper"></a>

----------------------------------------------------------------

Please report any bugs or queries by [raising a GitHub issue](https://github.com/KRR-Oxford/DeepOnto/issues/new/choose) or sending emails to the maintainers (Yuan He or Jiaoyan Chen) through:

> first_name.last_name@cs.ox.ac.uk
