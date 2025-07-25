#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS

check_info = {}

# Example output from agent:
# <<<emcvnx_raidgroups>>>
#
#
# Server IP Address:       172.16.8.82
# Agent Rev:           7.32.27 (0.14)
#
#
# All RAID Groups Information
# ----------------------------
#
#
# RaidGroup ID:                              0
# RaidGroup Type:                            r5
# RaidGroup State:                           Explicit_Remove
#                                            Valid_luns
# List of disks:                             Bus 0 Enclosure 0  Disk 0
#                                            Bus 0 Enclosure 0  Disk 1
#                                            Bus 0 Enclosure 0  Disk 2
#                                            Bus 0 Enclosure 0  Disk 3
# List of luns:                              4
# Max Number of disks:                       16
# Max Number of luns:                        256
# Raw Capacity (Blocks):                     702504960
# Logical Capacity (Blocks):                 526878720
# Free Capacity (Blocks,non-contiguous):     0
# Free contiguous group of unbound segments: 0
# Defrag/Expand priority:                    Medium
# Percent defragmented:                      100
# Percent expanded:                          N/A
# Disk expanding onto:                       N/A
# Lun Expansion enabled:                     NO
# Legal RAID types:                          r5
#
# RaidGroup ID:                              124
# RaidGroup Type:                            hot_spare
# [...]

# Parse agent output into a dict of the form:
# (where the RAID Group ID is used as key)
# parsed = {'0':   {'luns': '4'},
#           '1':   {'luns': '0,1'},
#           '124': {'luns': '4089'},
#           '2':   {'luns': '2,3'}}


def parse_emcvnx_raidgroups(info):
    parsed = {}
    append = False
    for line in info:
        if len(line) > 2 and line[0] == "RaidGroup" and line[1] == "ID:":
            rg: dict[str, str | list] = {}
            parsed[line[2]] = rg
        elif len(line) > 3 and line[0] == "List" and line[1] == "of" and line[2] == "luns:":
            rg["luns"] = ",".join(line[3:])
        elif len(line) > 8 and line[0] == "List" and line[1] == "of" and line[2] == "disks:":
            disks = []
            disk = line[4] + "/" + line[6] + " Disk " + line[8]
            disks.append(disk)
            rg["disks"] = disks
            append = True
        elif (
            append is True
            and len(line) > 5
            and line[0] == "Bus"
            and line[2] == "Enclosure"
            and line[4] == "Disk"
        ):
            disk = line[1] + "/" + line[3] + " Disk " + line[5]
            disks.append(disk)
        elif append is True:
            append = False
        elif (
            len(line) > 3 and line[0] == "Raw" and line[1] == "Capacity" and line[2] == "(Blocks):"
        ):
            rg["capacity_raw_blocks"] = line[3]
        elif (
            len(line) > 3
            and line[0] == "Logical"
            and line[1] == "Capacity"
            and line[2] == "(Blocks):"
        ):
            rg["capacity_logical_blocks"] = line[3]
        elif (
            len(line) > 3
            and line[0] == "Free"
            and line[1] == "Capacity"
            and line[2] == "(Blocks,non-contiguous):"
        ):
            rg["capacity_free_total_blocks"] = line[3]
        elif (
            len(line) > 6
            and line[0] == "Free"
            and line[1] == "contiguous"
            and line[4] == "unbound"
            and line[5] == "segments:"
        ):
            rg["capacity_free_contiguous_blocks"] = line[6]
    return parsed


check_info["emcvnx_raidgroups"] = LegacyCheckDefinition(
    name="emcvnx_raidgroups",
    parse_function=parse_emcvnx_raidgroups,
)


def inventory_emcvnx_raidgroups(section):
    inventory = []
    for rg in section:
        inventory.append((rg, None))
    return inventory


#   .--list of LUNs--------------------------------------------------------.
#   |           _ _     _            __   _    _   _ _   _                 |
#   |          | (_)___| |_    ___  / _| | |  | | | | \ | |___             |
#   |          | | / __| __|  / _ \| |_  | |  | | | |  \| / __|            |
#   |          | | \__ \ |_  | (_) |  _| | |__| |_| | |\  \__ \            |
#   |          |_|_|___/\__|  \___/|_|   |_____\___/|_| \_|___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_emcvnx_raidgroups_list_luns(item, _no_params, section):
    if item not in section:
        return 3, "RAID Group %s not found in agent output" % item
    return 0, "List of LUNs: " + section[item]["luns"]


check_info["emcvnx_raidgroups.list_luns"] = LegacyCheckDefinition(
    name="emcvnx_raidgroups_list_luns",
    service_name="RAID Group %s LUNs",
    sections=["emcvnx_raidgroups"],
    discovery_function=inventory_emcvnx_raidgroups,
    check_function=check_emcvnx_raidgroups_list_luns,
)

# .
#   .--list of disks-------------------------------------------------------.
#   |           _ _     _            __       _ _     _                    |
#   |          | (_)___| |_    ___  / _|   __| (_)___| | _____             |
#   |          | | / __| __|  / _ \| |_   / _` | / __| |/ / __|            |
#   |          | | \__ \ |_  | (_) |  _| | (_| | \__ \   <\__ \            |
#   |          |_|_|___/\__|  \___/|_|    \__,_|_|___/_|\_\___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_emcvnx_raidgroups_list_disks(item, _no_params, section):
    if item not in section:
        return 3, "RAID Group %s not found in agent output" % item

    message = ""
    enc = ""
    for disk in sorted(section[item]["disks"]):
        if message != "":
            message += ", "
        enc_id, disk_id = disk.split(" ", 1)
        if enc_id == enc:
            message += disk_id
        else:
            message += "Enclosure " + enc_id + " " + disk_id
            enc = enc_id

    return 0, "List of Disks: " + message


check_info["emcvnx_raidgroups.list_disks"] = LegacyCheckDefinition(
    name="emcvnx_raidgroups_list_disks",
    service_name="RAID Group %s Disks",
    sections=["emcvnx_raidgroups"],
    discovery_function=inventory_emcvnx_raidgroups,
    check_function=check_emcvnx_raidgroups_list_disks,
)

# .
#   .--capacity------------------------------------------------------------.
#   |                                          _ _                         |
#   |                ___ __ _ _ __   __ _  ___(_) |_ _   _                 |
#   |               / __/ _` | '_ \ / _` |/ __| | __| | | |                |
#   |              | (_| (_| | |_) | (_| | (__| | |_| |_| |                |
#   |               \___\__,_| .__/ \__,_|\___|_|\__|\__, |                |
#   |                        |_|                     |___/                 |
#   '----------------------------------------------------------------------'


def inventory_emcvnx_raidgroups_capacity(section):
    inventory = []
    for rg in section:
        inventory.append((rg, {}))
    return inventory


def check_emcvnx_raidgroups_capacity(item, params, section):
    if item not in section:
        return 3, "RAID Group %s not found in agent output" % item

    fslist = []
    # Blocksize in Bytes, seems to be fix
    # (is not listed in the naviseccli output anywhere)
    blocksize = 512
    size_mb = int(section[item]["capacity_logical_blocks"]) * blocksize / 1048576.0
    avail_mb = int(section[item]["capacity_free_total_blocks"]) * blocksize / 1048576.0
    fslist.append((item, size_mb, avail_mb, 0))

    # variable name in perfdata is not allowed to be just a number
    # especially 0 does not work, so prefix it generally with "rg"
    rc, message, perfdata = df_check_filesystem_list(item, params, fslist)
    # note: on very first run perfdata is empty
    if len(perfdata) > 0:
        perfdata[0] = (
            "rg" + perfdata[0][0],
            perfdata[0][1],
            perfdata[0][2],
            perfdata[0][3],
            perfdata[0][4],
            perfdata[0][5],
        )
    return rc, message, perfdata


check_info["emcvnx_raidgroups.capacity"] = LegacyCheckDefinition(
    name="emcvnx_raidgroups_capacity",
    service_name="RAID Group %s Capacity",
    sections=["emcvnx_raidgroups"],
    discovery_function=inventory_emcvnx_raidgroups_capacity,
    check_function=check_emcvnx_raidgroups_capacity,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)

# .
#   .--capacity contiguous-------------------------------------------------.
#   |                          _   _                                       |
#   |           ___ ___  _ __ | |_(_) __ _ _   _  ___  _   _ ___           |
#   |          / __/ _ \| '_ \| __| |/ _` | | | |/ _ \| | | / __|          |
#   |         | (_| (_) | | | | |_| | (_| | |_| | (_) | |_| \__ \          |
#   |          \___\___/|_| |_|\__|_|\__, |\__,_|\___/ \__,_|___/          |
#   |                                |___/                                 |
#   '----------------------------------------------------------------------'


def inventory_emcvnx_raidgroups_capacity_contiguous(section):
    inventory = []
    for rg in section:
        inventory.append((rg, {}))
    return inventory


def check_emcvnx_raidgroups_capacity_contiguous(item, params, section):
    if item not in section:
        return 3, "RAID Group %s not found in agent output" % item

    fslist = []
    # Blocksize in Bytes, seems to be fix
    # (is not listed in the naviseccli output anywhere)
    blocksize = 512
    size_mb = int(section[item]["capacity_logical_blocks"]) * blocksize / 1048576.0
    avail_mb = int(section[item]["capacity_free_contiguous_blocks"]) * blocksize / 1048576.0
    fslist.append((item, size_mb, avail_mb, 0))

    # variable name in perfdata is not allowed to be just a number
    # especially 0 does not work, so prefix it generally with "rg"
    rc, message, perfdata = df_check_filesystem_list(item, params, fslist)
    perfdata[0] = (
        "rg" + perfdata[0][0],
        perfdata[0][1],
        perfdata[0][2],
        perfdata[0][3],
        perfdata[0][4],
        perfdata[0][5],
    )
    return rc, message, perfdata


check_info["emcvnx_raidgroups.capacity_contiguous"] = LegacyCheckDefinition(
    name="emcvnx_raidgroups_capacity_contiguous",
    service_name="RAID Group %s Capacity Contiguous",
    sections=["emcvnx_raidgroups"],
    discovery_function=inventory_emcvnx_raidgroups_capacity_contiguous,
    check_function=check_emcvnx_raidgroups_capacity_contiguous,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)

# .
