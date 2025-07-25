#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

import cmk.gui.nagvis._hosttags
from cmk.gui.watolib.tags import TagConfigFile
from cmk.gui.watolib.utils import multisite_dir
from cmk.utils import tags
from cmk.utils.tags import TagGroupID, TagID


def _tag_test_cfg():
    return {
        "tag_groups": [
            {
                "id": "criticality",
                "title": "Criticality",
                "tags": [
                    {"id": "prod", "title": "Productive system", "aux_tags": ["bla"]},
                    {"id": "critical", "title": "Business critical", "aux_tags": []},
                    {"id": "test", "title": "Test system", "aux_tags": []},
                    {
                        "id": "offline",
                        "title": "Do not monitor this host",
                        "aux_tags": [],
                    },
                ],
            },
            {
                "id": "networking",
                "title": "Networking Segment",
                "tags": [
                    {
                        "id": "lan",
                        "title": "Local network (low latency)",
                        "aux_tags": [],
                    },
                    {"id": "wan", "title": "WAN (high latency)", "aux_tags": []},
                    {
                        "id": "dmz",
                        "title": "DMZ (low latency, secure access)",
                        "aux_tags": [],
                    },
                ],
            },
        ],
        "aux_tags": [{"id": "bla", "title": "bläää"}],
    }


@pytest.fixture()
def test_cfg() -> Iterator[tags.TagConfig]:
    multisite_dir().mkdir(parents=True, exist_ok=True)
    tags_mk = multisite_dir() / "tags.mk"
    hosttags_mk = multisite_dir() / "hosttags.mk"

    with tags_mk.open("w", encoding="utf-8") as f:
        f.write(
            """# Created by WATO
# encoding: utf-8

wato_tags = %s
"""
            % repr(_tag_test_cfg())
        )

    with hosttags_mk.open("w", encoding="utf-8") as f:
        f.write("")

    cfg = tags.TagConfig.from_config(TagConfigFile().load_for_reading())

    yield cfg

    if tags_mk.exists():
        tags_mk.unlink()


def test_tag_config_load(request_context: None, test_cfg: tags.TagConfig) -> None:
    assert len(test_cfg.tag_groups) == 2
    assert len(test_cfg.aux_tag_list.get_tags()) == 1


@pytest.mark.usefixtures("test_cfg")
def test_tag_config_save(mocker: MockerFixture) -> None:
    export_mock = mocker.patch.object(cmk.gui.nagvis._hosttags, "_export_hosttags_to_php")

    config_file = TagConfigFile()
    base_config_mock = mocker.patch.object(config_file, "_save_base_config")

    cfg = tags.TagConfig()
    cfg.insert_tag_group(
        tags.TagGroup.from_config(
            {
                "id": TagGroupID("tgid2"),
                "topic": "Topics",
                "title": "titlor",
                "tags": [{"id": TagID("tgid2"), "title": "tagid2", "aux_tags": []}],
            }
        )
    )
    config_file.save(cfg.get_dict_format(), pprint_value=False)

    export_mock.assert_called_once()
    base_config_mock.assert_called_once()

    cfg = tags.TagConfig.from_config(config_file.load_for_reading())
    assert len(cfg.tag_groups) == 1
    assert cfg.tag_groups[0].id == "tgid2"
