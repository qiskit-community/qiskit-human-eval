# qiskit-humaneval

In this repository you will find `qiskit-humaneval` a dataset for evaluating LLM's at writing Qiskit code.

## Dataset

The Qiskit HumanEval dataset is inspired by OpenAI's [HumanEval](https://github.com/openai/human-eval). It includes 151 Qiskit problems written by human Qiskit advocates.

We provide two versions of the dataset:
- In [qiskit_humaneval](dataset/dataset_qiskit_test_human_eval.json) the prompt includes import statements, function header and signature, and a doctring with the problem to solve. For example, sample 1:
```python
from qiskit import QuantumCircuit
def create_quantum_circuit(n_qubits):
    """ Generate a Quantum Circuit for the given int 'n_qubits' and return it.
    """
```
- In [qiskit_humaneval_hard](dataset/dataset_qiskit_test_human_eval.json) the prompt only includes the problem statement and the model is asked to create a function answering the problem. This is much harder for the LLM as the imports are not provided. For example, sample 1:
```
Generate a Quantum Circuit for the given int 'n_qubits' and return it.
You must implement this using a function named `create_quantum_circuit` with the following arguments: n_qubits.
```

## Requirements Setup

Install required dependencies using `pip`:
```
pip install -r requirements.txt
```

`Graphviz` is required for graphical visualization generation, refer to [Graphviz official site](https://graphviz.org/download/) for software download instructions.


## Contribution Guidelines

If you'd like to contribute to the Qiskit HumanEval, please take a look at our [contribution guidelines](CONTRIBUTING.md). By participating, you are expected to uphold our [code of conduct](CODE_OF_CONDUCT.md).

## Terms of use

* Terms of use: [https://quantum.ibm.com/terms](https://quantum.ibm.com/terms)
* Privacy policy: [https://quantum.ibm.com/terms/privacy](https://quantum.ibm.com/terms/privacy)

## License

[Apache License 2.0](LICENSE)
