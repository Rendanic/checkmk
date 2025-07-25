#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.gui import sites, user_sites
from cmk.livestatus_client import (
    NetworkSocketDetails,
    SiteConfiguration,
    SiteConfigurations,
    UnixSocketDetails,
)


def default_site_config() -> SiteConfiguration:
    return SiteConfiguration(
        {
            "id": SiteId("mysite"),
            "alias": "Local site mysite",
            "socket": ("local", None),
            "disable_wato": True,
            "disabled": False,
            "insecure": False,
            "url_prefix": "/mysite/",
            "multisiteurl": "",
            "persist": False,
            "replicate_ec": False,
            "replicate_mkps": False,
            "replication": None,
            "timeout": 5,
            "user_login": True,
            "proxy": None,
            "user_sync": "all",
            "status_host": None,
            "message_broker_port": 5672,
        }
    )


def test_encode_socket_for_livestatus_local() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"), default_site_config() | {"socket": ("local", None), "proxy": None}
        )
        == f"unix:{cmk.utils.paths.omd_root}/tmp/run/live"
    )


def test_encode_socket_for_livestatus_local_liveproxy() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config() | {"socket": ("local", None), "proxy": {"params": None}},
        )
        == f"unix:{cmk.utils.paths.omd_root}/tmp/run/liveproxy/mysite"
    )


def test_encode_socket_for_livestatus_unix() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config()
            | {"socket": ("unix", UnixSocketDetails(path="/a/b/c")), "proxy": None},
        )
        == "unix:/a/b/c"
    )


def test_encode_socket_for_livestatus_unix_liveproxy() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config()
            | {"socket": ("unix", UnixSocketDetails(path="/a/b/c")), "proxy": {"params": None}},
        )
        == f"unix:{cmk.utils.paths.omd_root}/tmp/run/liveproxy/mysite"
    )


def test_encode_socket_for_livestatus_tcp() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config()
            | {
                "socket": (
                    "tcp",
                    NetworkSocketDetails(address=("127.0.0.1", 1234), tls=("plain_text", {})),
                ),
                "proxy": None,
            },
        )
        == "tcp:127.0.0.1:1234"
    )


def test_encode_socket_for_livestatus_tcp6() -> None:
    assert (
        sites.encode_socket_for_livestatus(
            SiteId("mysite"),
            default_site_config()
            | {
                "socket": (
                    "tcp6",
                    NetworkSocketDetails(address=("::1", 1234), tls=("plain_text", {})),
                ),
                "proxy": None,
            },
        )
        == "tcp6:::1:1234"
    )


def test_site_config_for_livestatus_tcp_tls() -> None:
    site_config = sites._site_config_for_livestatus(
        SiteId("mysite"),
        default_site_config()
        | {
            "socket": (
                "tcp",
                NetworkSocketDetails(
                    address=("127.0.0.1", 1234), tls=("encrypted", {"verify": True})
                ),
            ),
            "proxy": None,
        },
    )
    assert site_config["socket"] == "tcp:127.0.0.1:1234"
    assert site_config["tls"] == ("encrypted", {"verify": True})
    assert site_config["proxy"] is None


def test_sorted_sites(request_context: None) -> None:
    expected = [
        ("site1", "Site 1"),
        ("site12", "Site 12"),
        ("site23", "Site 23"),
        ("site3", "Site 3"),
        ("site5", "Site 5"),
        ("site6", "Site 6"),
    ]
    assert (
        user_sites.sorted_sites(
            SiteConfigurations(
                {
                    SiteId("site1"): _site_config(SiteId("site1"), "Site 1"),
                    SiteId("site3"): _site_config(SiteId("site3"), "Site 3"),
                    SiteId("site5"): _site_config(SiteId("site5"), "Site 5"),
                    SiteId("site6"): _site_config(SiteId("site6"), "Site 6"),
                    SiteId("site12"): _site_config(SiteId("site12"), "Site 12"),
                    SiteId("site23"): _site_config(SiteId("site23"), "Site 23"),
                }
            )
        )
        == expected
    )


def _site_config(site_id: SiteId, alias: str) -> SiteConfiguration:
    return SiteConfiguration(
        {
            "id": site_id,
            "alias": alias,
            "socket": ("local", None),
            "disable_wato": True,
            "disabled": False,
            "insecure": False,
            "url_prefix": "/mysite/",
            "multisiteurl": "",
            "persist": False,
            "replicate_ec": False,
            "replicate_mkps": False,
            "replication": "slave",
            "timeout": 5,
            "user_login": True,
            "proxy": None,
            "user_sync": "all",
            "status_host": None,
            "message_broker_port": 5672,
        }
    )
