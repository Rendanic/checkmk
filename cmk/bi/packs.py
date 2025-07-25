#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple, NotRequired, TypedDict

from marshmallow import pre_dump

from cmk import fields
from cmk.bi.actions import (
    BICallARuleAction,
    BIStateOfHostAction,
    BIStateOfRemainingServicesAction,
    BIStateOfServiceAction,
)
from cmk.bi.aggregation import BIAggregation, BIAggregationSchema
from cmk.bi.lib import ReqBoolean, ReqList, ReqNested, ReqString
from cmk.bi.node_generator import BINodeGenerator
from cmk.bi.rule import BIRule, BIRuleSchema
from cmk.bi.rule_interface import bi_rule_id_registry
from cmk.bi.sample_configs import bi_sample_config
from cmk.bi.schema import Schema
from cmk.bi.search import BIHostSearch, BIServiceSearch
from cmk.bi.type_defs import AggrConfigDict
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _
from cmk.fields import String
from cmk.utils.paths import var_dir

_ContactgroupName = str


class DeleteErrorUsedByAggregation(MKGeneralException):
    pass


class DeleteErrorUsedByRule(MKGeneralException):
    pass


class RuleNotFoundException(MKGeneralException):
    pass


class PackNotFoundException(MKGeneralException):
    pass


class AggregationNotFoundException(MKGeneralException):
    pass


class RuleReferencesResult(NamedTuple):
    aggr_refs: int
    rule_refs: int
    level: int


#   .--Packs---------------------------------------------------------------.
#   |                      ____            _                               |
#   |                     |  _ \ __ _  ___| | _____                        |
#   |                     | |_) / _` |/ __| |/ / __|                       |
#   |                     |  __/ (_| | (__|   <\__ \                       |
#   |                     |_|   \__,_|\___|_|\_\___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BIPackConfig(TypedDict):
    id: str
    title: str
    comment: NotRequired[str]
    contact_groups: list[_ContactgroupName]
    public: bool
    rules: NotRequired[list[dict[str, Any]]]
    aggregations: NotRequired[list[AggrConfigDict]]


class BIAggregationPack:
    def __init__(self, pack_config: BIPackConfig) -> None:
        super().__init__()
        self.id = pack_config["id"]
        self.title = pack_config["title"]
        self.comment = pack_config.get("comment", "")
        self.contact_groups = pack_config["contact_groups"]
        self.public = pack_config["public"]

        self.rules = {x["id"]: BIRule(x, self.id) for x in pack_config.get("rules", [])}
        self.aggregations = {
            x["id"]: BIAggregation(x, self.id) for x in pack_config.get("aggregations", [])
        }

    @classmethod
    def schema(cls) -> type["BIAggregationPackSchema"]:
        return BIAggregationPackSchema

    def serialize(self) -> BIPackConfig:
        return BIPackConfig(
            id=self.id,
            title=self.title,
            comment=self.comment,
            contact_groups=self.contact_groups,
            public=self.public,
            rules=[rule.serialize() for rule in self.rules.values()],
            aggregations=[aggr.serialize() for aggr in self.aggregations.values()],
        )

    def num_aggregations(self) -> int:
        return len(self.aggregations)

    def num_rules(self) -> int:
        return len(self.rules)

    def get_rules(self) -> dict[str, BIRule]:
        return self.rules

    def get_aggregations(self) -> dict[str, BIAggregation]:
        return self.aggregations

    def add_rule(self, bi_rule: BIRule) -> None:
        self.rules[bi_rule.id] = bi_rule

    def delete_rule(self, rule_id: str) -> None:
        """Deletes a rule without rule tree integrity check"""
        del self.rules[rule_id]

    def get_rule(self, rule_id: str) -> BIRule | None:
        return self.rules.get(rule_id)

    def get_rule_mandatory(self, rule_id: str) -> BIRule:
        return self.rules[rule_id]

    def add_aggregation(self, bi_aggregation: BIAggregation) -> None:
        self.aggregations[bi_aggregation.id] = bi_aggregation

    def delete_aggregation(self, aggregation_id: str) -> None:
        del self.aggregations[aggregation_id]

    def get_aggregation(self, aggregation_id: str) -> BIAggregation | None:
        return self.aggregations.get(aggregation_id)

    def get_aggregation_mandatory(self, aggregation_id: str) -> BIAggregation:
        return self.aggregations[aggregation_id]


class BIAggregationPacks:
    def __init__(self, bi_configuration_file: Path) -> None:
        super().__init__()
        self.packs: dict[str, BIAggregationPack] = {}
        self._bi_configuration_file = bi_configuration_file

    @classmethod
    def schema(cls) -> type["BIAggregationPacksSchema"]:
        return BIAggregationPacksSchema

    def cleanup(self) -> None:
        self.packs.clear()
        bi_rule_id_registry.clear()

    def pack_exists(self, pack_id: str) -> bool:
        return pack_id in self.packs

    def get_packs(self) -> dict[str, BIAggregationPack]:
        return self.packs

    def add_pack(self, pack: BIAggregationPack) -> None:
        self.packs[pack.id] = pack

    def get_pack(self, pack_id: str) -> BIAggregationPack | None:
        return self.packs.get(pack_id)

    def get_pack_mandatory(self, pack_id: str) -> BIAggregationPack:
        if pack := self.packs.get(pack_id):
            return pack
        raise PackNotFoundException(_("The requested pack_id does not exist"))

    def delete_pack(self, pack_id: str) -> None:
        del self.packs[pack_id]

    def get_rule(self, rule_id: str) -> BIRule | None:
        for bi_pack in self.packs.values():
            if bi_rule := bi_pack.get_rule(rule_id):
                return bi_rule
        return None

    def get_rule_mandatory(self, rule_id: str) -> BIRule:
        if bi_rule := self.get_rule(rule_id):
            return bi_rule
        raise RuleNotFoundException(_("The requested BI rule does not exist."))

    def delete_rule(self, rule_id: str) -> None:
        # Only delete a rule if it is not referenced by other rules/aggregations
        references = self.count_rule_references(rule_id)
        if references.aggr_refs:
            raise DeleteErrorUsedByAggregation(
                _("You cannot delete this rule: it is still used by other aggregations.")
            )
        if references.rule_refs:
            raise DeleteErrorUsedByRule(
                _("You cannot delete this rule: it is still used by other rules.")
            )

        for bi_pack in self.packs.values():
            if bi_pack.get_rule(rule_id) is not None:
                bi_pack.delete_rule(rule_id)
                break

    def get_all_rules(self) -> list[BIRule]:
        return [
            bi_rule for bi_pack in self.packs.values() for bi_rule in bi_pack.get_rules().values()
        ]

    def get_aggregation_group_trees(self) -> list[str]:
        all_groups: set[str] = set()
        for aggregation in self.get_all_aggregations():
            if aggregation.computation_options.disabled:
                continue
            all_groups.update(["/".join(x) for x in aggregation.groups.paths])
        return sorted(all_groups)

    def get_aggregation_group_choices(self) -> list[tuple[str, str]]:
        """Return a list of all available group names and fully combined group paths"""
        all_groups: set[str] = set()
        for aggregation in self.get_all_aggregations():
            if aggregation.computation_options.disabled:
                continue
            all_groups.update(map(str, aggregation.groups.names))
            all_groups.update(["/".join(x) for x in aggregation.groups.paths])
        return [(gn, gn) for gn in sorted(all_groups, key=lambda x: x.lower())]

    def get_aggregation(self, aggregation_id: str) -> BIAggregation | None:
        for bi_pack in self.packs.values():
            if bi_aggregation := bi_pack.get_aggregation(aggregation_id):
                return bi_aggregation
        return None

    def delete_aggregation(self, aggregation_id: str) -> None:
        for bi_pack in self.packs.values():
            if bi_pack.get_aggregation(aggregation_id):
                bi_pack.delete_aggregation(aggregation_id)
                break

    def get_aggregation_mandatory(self, aggregation_id: str) -> BIAggregation:
        if bi_aggregation := self.get_aggregation(aggregation_id):
            return bi_aggregation
        raise AggregationNotFoundException(_("The requested BI aggregation does not exist."))

    def get_all_aggregations(self) -> list[BIAggregation]:
        aggregations: list[BIAggregation] = []
        for bi_pack in self.packs.values():
            aggregations.extend(bi_pack.get_aggregations().values())
        return aggregations

    def get_pack_of_rule(self, rule_id: str) -> BIAggregationPack | None:
        for bi_pack in self.packs.values():
            if bi_pack.get_rule(rule_id) is not None:
                return bi_pack
        return None

    def get_pack_of_aggregation(self, aggr_id: str) -> BIAggregationPack | None:
        for bi_pack in self.packs.values():
            if bi_pack.get_aggregation(aggr_id) is not None:
                return bi_pack
        return None

    def get_rule_ids_of_aggregation(self, aggr_id: str) -> set[str]:
        bi_aggregation = self.get_aggregation_mandatory(aggr_id)
        if isinstance(bi_aggregation.node.action, BICallARuleAction):
            return set(self._get_rule_ids_of_rule(bi_aggregation.node.action.rule_id))
        return set()

    def _get_rule_ids_of_rule(self, rule_id: str) -> Iterator[str]:
        yield rule_id
        for bi_node in self.get_rule_mandatory(rule_id).get_nodes():
            if isinstance(bi_node.action, BICallARuleAction):
                yield from self._get_rule_ids_of_rule(bi_node.action.rule_id)

    def rename_rule_id(self, old_id: str, new_id: str) -> None:
        # Rename the rule itself and all call_a_rule references in rules and aggregations
        for bi_pack in self.packs.values():
            for bi_rule in list(bi_pack.get_rules().values()):
                if bi_rule.id == old_id:
                    bi_pack.delete_rule(old_id)
                    bi_rule.id = new_id
                    bi_pack.add_rule(bi_rule)

                for bi_node in bi_rule.get_nodes():
                    if (
                        isinstance(bi_node.action, BICallARuleAction)
                        and bi_node.action.rule_id == old_id
                    ):
                        bi_node.action.rule_id = new_id

            for bi_aggregation in bi_pack.get_aggregations().values():
                if (
                    isinstance(bi_aggregation.node.action, BICallARuleAction)
                    and bi_aggregation.node.action.rule_id == old_id
                ):
                    bi_aggregation.node.action.rule_id = new_id

    def load_config(self) -> None:
        if not self._bi_configuration_file.exists():
            self._load_config(bi_sample_config)
            return
        self._load_config(store.load_object_from_file(self._bi_configuration_file, default=None))

    def _load_config(self, config: dict) -> None:
        self.cleanup()
        self._instantiate_packs(config["packs"])

    def _instantiate_packs(self, packs_data: list[BIPackConfig]) -> None:
        self.packs = {x["id"]: BIAggregationPack(x) for x in packs_data}

    def save_config(self) -> None:
        store.save_text_to_file(self._bi_configuration_file, repr(self.generate_config()))
        enabled_aggregations = str(
            len(
                [
                    bi_aggr
                    for bi_aggr in self.get_all_aggregations()
                    if not bi_aggr.computation_options.disabled
                ]
            )
        )

        self._num_enabled_aggregations_dir().mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_text_to_file(self._num_enabled_aggregations_path(), enabled_aggregations)

    @classmethod
    def _num_enabled_aggregations_dir(cls) -> Path:
        return var_dir / "wato"

    @classmethod
    def _num_enabled_aggregations_path(cls) -> Path:
        return cls._num_enabled_aggregations_dir() / "num_enabled_aggregations"

    @classmethod
    def get_num_enabled_aggregations(cls) -> int:
        try:
            return int(store.load_text_from_file(cls._num_enabled_aggregations_path()))
        except (TypeError, ValueError):
            return 0

    def generate_config(self) -> dict[str, Any]:
        self._check_rule_cycles()
        return self.serialize()

    def serialize(self):
        return {"packs": [pack.serialize() for pack in self.packs.values()]}

    def _check_rule_cycles(self) -> None:
        """We have to check all rules for cycles.
        Previously only toplevel rules (those configured in aggregations) were parsed.
        However, it is impossible to determine the actual toplevel rules, because doing so
        could lead to rule cycles...
        """
        for bi_rule in self.get_all_rules():
            self._traverse_rule(bi_rule, [])

    def _traverse_rule(self, bi_rule: BIRule, parents: list[str]) -> None:
        if bi_rule.id in parents:
            parents.append(bi_rule.id)
            raise MKGeneralException(
                _(
                    "There is a cycle in your rules. This rule calls itself - "
                    "either directly or indirectly: %s"
                )
                % "->".join(parents)
            )

        parents.append(bi_rule.id)
        for node in bi_rule.nodes:
            if isinstance(node.action, BICallARuleAction):
                self._traverse_rule(self.get_rule_mandatory(node.action.rule_id), list(parents))

    def count_rule_references(self, check_rule_id: str) -> RuleReferencesResult:
        aggr_refs = 0
        for bi_aggregation in self.get_all_aggregations():
            if (
                isinstance(bi_aggregation.node.action, BICallARuleAction)
                and bi_aggregation.node.action.rule_id == check_rule_id
            ):
                aggr_refs += 1

        level = 0
        rule_refs = 0
        for bi_rule in self.get_all_rules():
            lv = self._rule_uses_rule(bi_rule, check_rule_id)
            level = max(lv, level)
            if lv == 1:
                rule_refs += 1

        return RuleReferencesResult(aggr_refs, rule_refs, level)

    def _rule_uses_rule(self, bi_rule: BIRule, check_rule_id: str, level: int = 0) -> int:
        for bi_node in bi_rule.get_nodes():
            if isinstance(bi_node.action, BICallARuleAction):
                node_rule_id = bi_node.action.rule_id
                if node_rule_id == check_rule_id:  # Rule is directly being used
                    return level + 1
                # Check if lower rules use it
                bi_subrule = self.get_rule_mandatory(node_rule_id)
                lv = self._rule_uses_rule(bi_subrule, check_rule_id, level + 1)
                if lv != -1:
                    return lv
        return -1


class BIAggregationPackSchema(Schema):
    id = ReqString(dump_default="", example="bi_pack1", description="BI Pack ID.")
    title = ReqString(dump_default="", example="BI Title", description="Title for the pack.")
    comment = String(
        description="An optional comment that may be used to explain the purpose of this object.",
        allow_none=True,
        example="Rule comment",
    )
    contact_groups = ReqList(
        fields.String(),
        dump_default=[],
        example=["contactgroup_a", "contactgroup_b"],
        description="List of permitted contact groups.",
    )
    public = ReqBoolean(
        dump_default=False,
        description="If the rule is not public, users must be administrators of members of a permitted contact group to use it.",
    )
    rules = ReqList(
        fields.Nested(BIRuleSchema()), dump_default=[], description="Rules in this BI pack."
    )
    aggregations = ReqList(
        fields.Nested(BIAggregationSchema()),
        dump_default=[],
        description="Aggregations in this BI pack.",
    )

    @pre_dump
    def pre_dumper(self, obj: BIAggregationPack, many: bool = False) -> dict:
        # Convert aggregations and rules to list
        return {
            "id": obj.id,
            "title": obj.title,
            "comment": obj.comment,
            "contact_groups": obj.contact_groups,
            "public": obj.public,
            "rules": obj.get_rules().values(),
            "aggregations": obj.get_aggregations().values(),
        }


class BIAggregationPacksSchema(Schema):
    packs = ReqList(ReqNested(BIAggregationPackSchema), description="List of BI packs.")

    @pre_dump
    def pre_dumper(self, obj: BIAggregationPacks, many: bool = False) -> dict:
        # Convert packs to list
        return {"packs": obj.packs.values()}


# .
#   .--Rename Hosts--------------------------------------------------------.
#   |   ____                                   _   _           _           |
#   |  |  _ \ ___ _ __   __ _ _ __ ___   ___  | | | | ___  ___| |_ ___     |
#   |  | |_) / _ \ '_ \ / _` | '_ ` _ \ / _ \ | |_| |/ _ \/ __| __/ __|    |
#   |  |  _ <  __/ | | | (_| | | | | | |  __/ |  _  | (_) \__ \ |_\__ \    |
#   |  |_| \_\___|_| |_|\__,_|_| |_| |_|\___| |_| |_|\___/|___/\__|___/    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Class just for renaming hosts in the BI configuration.              |
#   '----------------------------------------------------------------------'


class BIHostRenamer:
    def rename_host(self, oldname: str, newname: str, bi_packs: BIAggregationPacks) -> list[str]:
        bi_packs.load_config()
        renamed = 0

        for bi_pack in bi_packs.get_packs().values():
            for bi_rule in bi_pack.get_rules().values():
                renamed += sum(self.rename_node(x, oldname, newname) for x in bi_rule.nodes)

            for bi_aggregation in bi_pack.get_aggregations().values():
                renamed += self.rename_node(bi_aggregation.node, oldname, newname)

        if renamed:
            bi_packs.save_config()
            return ["bi"] * renamed
        return []

    def rename_node(self, bi_node: BINodeGenerator, oldname: str, newname: str) -> int:
        renamed = 0
        renamed += self.rename_node_action(bi_node, oldname, newname)
        renamed += self.rename_node_search(bi_node, oldname, newname)
        return renamed

    def rename_node_action(self, bi_node: BINodeGenerator, oldname: str, newname: str) -> int:
        # TODO: renaming can be moved into the action class itself. allows easier plug-ins
        if isinstance(
            bi_node.action,
            BIStateOfHostAction | BIStateOfServiceAction | BIStateOfRemainingServicesAction,
        ):
            if bi_node.action.host_regex == oldname:
                bi_node.action.host_regex = newname
                return 1

        elif isinstance(bi_node.action, BICallARuleAction):
            arguments = bi_node.action.params.arguments
            if oldname in arguments:
                new_arguments = [newname if x == oldname else x for x in arguments]
                bi_node.action.params.arguments = new_arguments
                return 1

        return 0

    def rename_node_search(self, bi_node: BINodeGenerator, oldname: str, newname: str) -> int:
        # TODO: renaming can be moved into the search class itself. allows easier plug-ins
        if (
            isinstance(bi_node.search, BIHostSearch | BIServiceSearch)
            and bi_node.search.conditions["host_choice"]["type"] == "host_name_regex"
            and bi_node.search.conditions["host_choice"]["pattern"] == oldname
        ):
            bi_node.search.conditions["host_choice"]["pattern"] = newname
            return 1

        return 0
