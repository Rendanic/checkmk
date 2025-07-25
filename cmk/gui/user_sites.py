#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from livestatus import SiteConfigurations

from cmk.ccc.site import omd_site, SiteId
from cmk.gui.config import active_config
from cmk.gui.logged_in import user as global_user
from cmk.gui.site_config import enabled_sites, is_replication_enabled, site_is_local


def sorted_sites(site_configs: SiteConfigurations) -> list[tuple[SiteId, str]]:
    return sorted(
        [
            (site_id, s["alias"])
            for site_id, s in global_user.authorized_sites(
                unfiltered_sites=enabled_sites(site_configs)
            ).items()
        ],
        key=lambda k: k[1].lower(),
    )


def get_configured_site_choices() -> list[tuple[SiteId, str]]:
    return site_choices(global_user.authorized_sites(unfiltered_sites=active_config.sites))


def site_attribute_default_value() -> SiteId | None:
    site_id = omd_site()
    authorized_site_ids = global_user.authorized_sites(unfiltered_sites=active_config.sites).keys()
    if site_id in authorized_site_ids:
        return site_id
    return None


def site_choices(site_configs: SiteConfigurations) -> list[tuple[SiteId, str]]:
    """Compute the choices to be used e.g. in dropdowns from a SiteConfigurations collection"""
    choices = []
    for site_id, site_spec in site_configs.items():
        title: str = site_id
        if site_spec.get("alias"):
            title += " - " + site_spec["alias"]

        choices.append((site_id, title))

    return sorted(choices, key=lambda s: s[1])


def get_event_console_site_choices() -> list[tuple[SiteId, str]]:
    return site_choices(
        SiteConfigurations(
            {
                site_id: site
                for site_id, site in global_user.authorized_sites(
                    unfiltered_sites=active_config.sites
                ).items()
                if site_is_local(site) or site.get("replicate_ec", False)
            }
        )
    )


def get_activation_site_choices() -> list[tuple[SiteId, str]]:
    return site_choices(activation_sites(active_config.sites))


def activation_sites(site_configs: SiteConfigurations) -> SiteConfigurations:
    """Returns sites that are affected by Setup changes

    These sites are shown on activation page and get change entries
    added during Setup changes."""
    return SiteConfigurations(
        {
            site_id: site
            for site_id, site in global_user.authorized_sites(unfiltered_sites=site_configs).items()
            if site_is_local(site) or is_replication_enabled(site)
        }
    )
