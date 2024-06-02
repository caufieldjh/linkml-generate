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

There may be some prompt-based ways to encourage more interesting generation, particularly if we’re generating examples in an attempt to find schema validation edge cases.

For extra fun, work backwards from the generated data and make text corresponding to it.

The LLM can also do this, of course.

Would also like to support creation of dynamically constructed example sets: just include filename and number of examples to use in each prompt within the schema.

### Promoting computational creativity

Creating synthetic data is only a useful task if the data is representative of some larger collection of observations (real or extrapolated) and/or it contains a range of variability.

Without explicit direction or parameter adjustment, LLMs aren't very good at the latter task - they tend to generate consistently boring results.

How may we stimulate their creativity?

1. Raise the temperature, but ensure adherence to the expected structure.
2. Explicitly define how entries should vary - this may be an iterative process. For example, if we want a list of fruits, it may help to state that the generated examples should vary in color. We don't always know the full range of properties applicable to a group of objects so generating a list of such properties may be a good start.
3. Include further detail in the starting schema. If generating a list of street addresses, for example, the LLM may rarely produce street numbers like "33A" unless provided with in-context examples or a field like "street number postfix" to contain these values.

## Related Work

* Synthea (<https://github.com/synthetichealth/synthea>)
