#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable

import pytest

from cmk.agent_based.v2 import DiscoveryResult, Result, Service, State
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckFunction,
    CheckPlugin,
    CheckPluginName,
)
from cmk.utils.sectionname import SectionName

check_name = "megaraid_bbu"

type DiscoveryFunction = Callable[..., DiscoveryResult]


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    return agent_based_plugins.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"parse_{check_name}")
def _get_parse_function(agent_based_plugins):
    return agent_based_plugins.agent_sections[SectionName(check_name)].parse_function


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{check_name}")
def _get_discovery_function(plugin: CheckPlugin) -> DiscoveryFunction:
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{check_name}")
def _get_check_function(plugin: CheckPlugin) -> CheckFunction:
    return lambda i, s: plugin.check_function(item=i, params={}, section=s)


@pytest.fixture(scope="function", name="section")
def _get_section(parse_megaraid_bbu):
    return parse_megaraid_bbu(
        [
            line.split()
            for line in """
BBU status for Adapter: 0

BatteryType: CVPM02
Voltage: 9437 mV
Current: 0 mA
Temperature: 27 C
BBU Firmware Status:

Charging Status : None
Voltage : OK
Temperature : OK
Learn Cycle Requested : No
Learn Cycle Active : No
Learn Cycle Status : OK
Learn Cycle Timeout : No
I2c Errors Detected : No
Battery Pack Missing : No
Battery Replacement required : No
Remaining Capacity Low : No
Periodic Learn Required : No
Transparent Learn : No
No space to cache offload : No
Pack is about to fail & should be replaced : No
Cache Offload premium feature required : No
Module microcode update required : No
BBU GasGauge Status: 0x6ef7
Pack energy : 247 J
Capacitance : 110
Remaining reserve space : 0
""".split("\n")
            if line
        ]
    )


def test_discovery(discover_megaraid_bbu: DiscoveryFunction, section: object) -> None:
    assert list(discover_megaraid_bbu(section)) == [Service(item="/c0")]


def test_check_ok(check_megaraid_bbu: CheckFunction, section: object) -> None:
    assert list(check_megaraid_bbu("/c0", section)) == [
        Result(
            state=State.OK,
            summary="Charge: not reported for this controller",
        ),
        Result(
            state=State.OK,
            summary="All states as expected",
        ),
    ]


def test_check_low_cap(
    check_megaraid_bbu: CheckFunction, section: dict[str, dict[str, str]]
) -> None:
    section["0"]["Remaining Capacity Low"] = "Yes"
    assert list(check_megaraid_bbu("/c0", section)) == [
        Result(
            state=State.OK,
            summary="Charge: not reported for this controller",
        ),
        Result(
            state=State.WARN,
            summary="Remaining capacity low: Yes (expected: No)",
        ),
    ]
