#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import override

from cmk.ccc.i18n import _
from cmk.rulesets.v1 import Label
from cmk.rulesets.v1.form_specs import BooleanChoice
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from .._type_defs import DefaultValue, IncomingData, InvalidValue
from .._utils import (
    compute_validators,
    get_title_and_help,
    localize,
)
from .._visitor_base import FormSpecVisitor
from ..validators import build_vue_validators

type _ParsedValueModel = bool
type _FallbackModel = bool


class BooleanChoiceVisitor(FormSpecVisitor[BooleanChoice, _ParsedValueModel, _FallbackModel]):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            return self.form_spec.prefill.value

        if not isinstance(raw_value.value, bool):
            return InvalidValue(
                reason=_("Invalid choice, falling back to False"), fallback_value=False
            )
        return raw_value.value

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.BooleanChoice, object]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.BooleanChoice(
                title=title,
                help=help_text,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(compute_validators(self.form_spec)),
                text_on=localize(Label("on")),
                text_off=localize(Label("off")),
            ),
            parsed_value.fallback_value if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> bool:
        return parsed_value
