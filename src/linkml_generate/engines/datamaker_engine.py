"""Class for generating data from a LinkML model.

Built on top of the `ontogpt` library and related to the the
SPIRES approach (SPIRESEngine in ontogpt) for performing schema-compliant
generations, though for producing data from scratch.
"""

import logging

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
import uuid

import pydantic
import yaml
from linkml_runtime.linkml_model import ClassDefinition, SlotDefinition
from oaklib import BasicOntologyInterface

from ontogpt.engines.knowledge_engine import (
    ANNOTATION_KEY_PROMPT,
    ANNOTATION_KEY_PROMPT_SKIP,
    EXAMPLE,
    FIELD,
    OBJECT,
    KnowledgeEngine,
    chunk_text,
)
from ontogpt.io.yaml_wrapper import dump_minimal_yaml
from ontogpt.templates.core import ExtractionResult

this_path = Path(__file__).parent

RESPONSE_ATOM = Union[str, "ResponseAtom"]  # type: ignore
RESPONSE_DICT = Dict[FIELD, Union[RESPONSE_ATOM, List[RESPONSE_ATOM]]]

@dataclass
class DataMakerEngine(KnowledgeEngine):
    """Data generation engine for LinkML models."""

    def make_data(
        self,
        cls: ClassDefinition = None,
        object: OBJECT = None,
        show_prompt: bool = False,
    ) -> ExtractionResult:
        """
        Make data compliant with the provided model.

        :param cls:
        :param object: optional stub object
        :return:
        """
        self.extracted_named_entities = [] # Clear the named entity buffer

        raw_text = self._raw_make(cls=cls, object=object, show_prompt=show_prompt)
        logging.info(f"RAW TEXT: {raw_text}")
        extracted_object = self.parse_completion_payload(
            raw_text, cls, object=object  # type: ignore
        )

        return ExtractionResult(
            input_text="",
            raw_completion_output=raw_text,
            prompt=self.last_prompt,
            extracted_object=extracted_object,
            named_entities=self.extracted_named_entities,
            # Note these are the named entities from the last generated entry,
            # not the full list of all named entities across all generations
        )

    def _extract_from_text_to_dict(self, text: str, cls: ClassDefinition = None) -> RESPONSE_DICT:
        raw_text = self._raw_make(text=text, cls=cls)
        return self._parse_response_to_dict(raw_text, cls)

    def _raw_make(
        self,
        cls: ClassDefinition = None,
        object: OBJECT = None,
        show_prompt: bool = False,
    ) -> str:
        """
        Extract annotations from the given text.

        :param text:
        :return:
        """
        prompt = self.get_completion_prompt(cls=cls, object=object)
        self.last_prompt = prompt
        payload = self.client.complete(prompt=prompt, show_prompt=show_prompt)
        return payload

    def get_completion_prompt(
        self, cls: ClassDefinition = None, object: OBJECT = None
    ) -> str:
        """Get the prompt for the given template, class, and slots."""
        if cls is None:
            cls = self.template_class

        prompt = "Produce a data object following this format:\n\n"

        for slot in self.schemaview.class_induced_slots(cls.name):
            if ANNOTATION_KEY_PROMPT_SKIP in slot.annotations:
                continue
            if ANNOTATION_KEY_PROMPT in slot.annotations:
                slot_prompt = slot.annotations[ANNOTATION_KEY_PROMPT].value
            elif slot.description:
                slot_prompt = slot.description
            else:
                if slot.multivalued:
                    slot_prompt = f"semicolon-separated list of {slot.name}s"
                else:
                    slot_prompt = f"the value for {slot.name}"
            if slot.range in self.schemaview.all_enums():
                enum_def = self.schemaview.get_enum(slot.range)
                pvs = [str(k) for k in enum_def.permissible_values.keys()]
                slot_prompt += f"Must be one of: {', '.join(pvs)}"
            prompt += f"{slot.name}: <{slot_prompt}>\n"
        if object:
            if cls is None:
                cls = self.template_class
            if isinstance(object, pydantic.BaseModel):
                object = object.model_dump()
            for k, v in object.items():
                if v:
                    slot = self.schemaview.induced_slot(k, cls.name)
                    prompt += f"{k}: {self._serialize_value(v, slot)}\n"
        return prompt

    def _parse_response_to_dict(
        self, results: str, cls: ClassDefinition = None
    ) -> Optional[RESPONSE_DICT]:
        """
        Parse the pseudo-YAML response from OpenAI into a dictionary object.

        E.g.

            foo: a; b; c

        becomes

            {"foo": ["a", "b", "c"]}

        :param results:
        :return:
        """
        lines = results.splitlines()
        ann = {}
        promptable_slots = self.promptable_slots(cls)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                if len(promptable_slots) == 1:
                    slot = promptable_slots[0]
                    logging.warning(
                        f"Coercing to YAML-like with key {slot.name}: Original line: {line}"
                    )
                    line = f"{slot.name}: {line}"
                else:
                    logging.error(f"Line '{line}' does not contain a colon; ignoring")
                    return None
            r = self._parse_line_to_dict(line, cls)
            if r is not None:
                field, val = r
                ann[field] = val
        return ann

    def _parse_line_to_dict(
        self, line: str, cls: ClassDefinition = None
    ) -> Optional[Tuple[FIELD, RESPONSE_ATOM]]:
        if cls is None:
            cls = self.template_class
        sv = self.schemaview
        # each line is a key-value pair
        logging.info(f"PARSING LINE: {line}")
        field, val = line.split(":", 1)
        # Field nornalization:
        # The LLML may mutate the output format somewhat,
        # randomly pluralizing or replacing spaces with underscores
        field = field.lower().replace(" ", "_")
        logging.debug(f"  FIELD: {field}")
        cls_slots = sv.class_slots(cls.name)
        slot = None
        if field in cls_slots:
            slot = sv.induced_slot(field, cls.name)
        else:
            # TODO: check this
            if field.endswith("s"):
                field = field[:-1]
            if field in cls_slots:
                slot = sv.induced_slot(field, cls.name)
        if not slot:
            logging.error(f"Cannot find slot for {field} in {line}")
            # raise ValueError(f"Cannot find slot for {field} in {line}")
            return None
        if not val:
            msg = f"Empty value in key-value line: {line}"
            if slot.required:
                raise ValueError(msg)
            if slot.recommended:
                logging.warning(msg)
            return None
        inlined = slot.inlined
        slot_range = sv.get_class(slot.range)
        if not inlined:
            if slot.range in sv.all_classes():
                inlined = sv.get_identifier_slot(slot_range.name) is None
        val = val.strip()
        if slot.multivalued:
            vals = [v.strip() for v in val.split(";")]
        else:
            vals = [val]
        vals = [val for val in vals if val]
        logging.debug(f"SLOT: {slot.name} INL: {inlined} VALS: {vals}")
        if inlined:
            vals = [
                self._extract_from_text_to_dict(v, slot_range) for v in vals  # type: ignore
            ]
        # transform back from list to single value if not multivalued
        if slot.multivalued:
            final_val = vals
        else:
            if len(vals) != 1:
                logging.error(f"Expected 1 value for {slot.name} in '{line}' but got {vals}")
            final_val = vals[0]  # type: ignore
        return field, final_val

    def parse_completion_payload(
        self, results: str, cls: ClassDefinition = None, object: dict = None
    ) -> pydantic.BaseModel:
        """
        Parse the completion payload into a pydantic class.

        :param results:
        :param cls:
        :param object: stub object
        :return:
        """
        raw = self._parse_response_to_dict(results, cls)
        logging.debug(f"RAW: {raw}")
        if object:
            raw = {**object, **raw}
        self._auto_add_ids(raw, cls)
        return self.ground_annotation_object(raw, cls)

    def _auto_add_ids(self, ann: RESPONSE_DICT, cls: ClassDefinition = None) -> None:
        if ann is None:
            return
        if cls is None:
            cls = self.template_class
        for slot in self.schemaview.class_induced_slots(cls.name):
            if slot.identifier:
                if slot.name not in ann:
                    auto_id = str(uuid.uuid4())
                    auto_prefix = self.auto_prefix
                    if slot.range == "uriorcurie" or slot.range == "uri":
                        ann[slot.name] = f"{auto_prefix}:{auto_id}"
                    else:
                        ann[slot.name] = auto_id

    def ground_annotation_object(
        self, ann: RESPONSE_DICT, cls: ClassDefinition = None
    ) -> Optional[pydantic.BaseModel]:
        """Ground the direct parse of the OpenAI payload.

        The raw openAI payload is a YAML-like string, which is parsed to
        a response dictionary.

        This dictionary is then grounded, using this method

        :param ann: Raw annotation object
        :param cls: schema class the ground object should instantiate
        :return: Grounded annotation object
        """
        logging.debug(f"Grounding annotation object {ann}")
        if cls is None:
            cls = self.template_class
        sv = self.schemaview
        new_ann: Dict[str, Any] = {}
        if ann is None:
            logging.error(f"Cannot ground None annotation, cls={cls.name}")
            return None
        for field, vals in ann.items():
            if isinstance(vals, list):
                multivalued = True
            else:
                multivalued = False
                vals = [vals]
            slot = sv.induced_slot(field, cls.name)
            rng_cls = sv.get_class(slot.range)
            enum_def = None
            if slot.range:
                if slot.range in self.schemaview.all_enums():
                    enum_def = self.schemaview.get_enum(slot.range)
            new_ann[field] = []
            logging.debug(f"FIELD: {field} SLOT: {slot.name}")
            for val in vals:
                if not val:
                    continue
                logging.debug(f"   VAL: {val}")
                if isinstance(val, tuple):
                    # special case for pairs
                    sub_slots = sv.class_induced_slots(rng_cls.name)
                    obj = {}
                    for i in range(0, len(val)):
                        sub_slot = sub_slots[i]
                        sub_rng = sv.get_class(sub_slot.range)
                        if not sub_rng:
                            logging.error(f"Cannot find range for {sub_slot.name}")
                        result = self.normalize_named_entity(val[i], sub_slot.range)
                        obj[sub_slot.name] = result
                elif isinstance(val, dict):
                    obj = self.ground_annotation_object(val, rng_cls)
                else:
                    obj = self.normalize_named_entity(val, slot.range)  # type: ignore
                if enum_def:
                    found = False
                    logging.info(f"Looking for {obj} in {enum_def.name}")
                    for k, _pv in enum_def.permissible_values.items():
                        if type(obj) is str and type(k) is str:
                            if obj.lower() == k.lower():  # type: ignore
                                obj = k  # type: ignore
                                found = True
                                break
                    if not found:
                        logging.info(f"Cannot find enum value for {obj} in {enum_def.name}")
                        obj = None
                if multivalued:
                    new_ann[field].append(obj)
                else:
                    new_ann[field] = obj
        logging.debug(f"Creating object from dict {new_ann}")
        logging.info(new_ann)
        py_cls = self.template_module.__dict__[cls.name]
        return py_cls(**new_ann)