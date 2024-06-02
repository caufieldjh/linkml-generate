# linkml-generate
An experimental approach to generating synthetic data based on LinkML schemas.

## Intended Uses

* _Testing schemas_: what fits the model? What should counterexamples look like? Do any intended counterexamples still pass validation?
* _Contextualizing documentation_: what does data look like when it adheres to the model? Descriptions are helpful, but what should the values be in practice?
* _Building synthetic data sets_: can we assemble more complete data collections based on current models and expectations?

## Operation

Example:

```
linkml-generate -vvv generate tests/input/food.yaml 
```

## Planned Functionality

This can look something like both OntoGPT and DRAGON-AI, in that it takes a LinkML schema as input and attempt to generate data items to fit each of the classes and slots.

ChatGPT on its own (with gpt-4o) does fairly well at this (see https://chatgpt.com/share/6df7f871-fb6d-4310-be3e-6c01930007ff)...

but it still hallucinates IDs and/or creates new IDs for existing terms.

So the strategy is:

1. generate text
2. attempt to ground,

OR

take more of a RAG strategy and preferentially generate text similar to that in a given ontology already, though with the occasional ungrounded value.

But we want to generate a whole set of data objects and have them be different, potentially in accordance with a pre-defined distribution.

(e.g., roughly equal numbers of male and female patients with some non-binary patients in there too) and/or some unspecified fields.

Maybe just a matter of tweaking the temperature? Still want to adhere to the structure though.

There may be some prompt-based ways to encourage more interesting generation, particularly if we’re generating examples in an attempt to find schema validation edge cases.

For extra fun, work backwards from the generated data and make text corresponding to it.

The LLM can also do this, of course.

Would also like to support creation of dynamically constructed example sets: just include filename and number of examples to use in each prompt within the schema.

## Related Work

* Synthea (<https://github.com/synthetichealth/synthea>)
