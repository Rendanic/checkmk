#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.base.api.agent_based.register as agent_based_register

SYS_DESCR_OID = ".1.3.6.1.2.1.1.1"

SYS_OBJID_OID = ".1.3.6.1.2.1.1.2"


@pytest.mark.usefixtures("config_load_all_checks")
def test_section_detection_uses_sysdescr_or_sysobjid():
    """Make sure the first OID is always either the system description
    or the system object ID. This increases performance massively.
    """

    known_exceptions = {
        # you should really have an exceptionally good reason to add something here.
        'dell_compellent_controller',
        'dell_compellent_disks',
        'dell_compellent_enclosure',
        'dell_compellent_folder',
        'dell_hw_info',
        'emerson_stat',
        'emerson_temp',
        'etherbox',
        'fast_lta_headunit',
        'fast_lta_silent_cubes',
        'fast_lta_volumes',
        'hp_proliant_cpu',
        'hp_proliant_da_cntlr',
        'hp_proliant_da_phydrv',
        'hp_proliant_fans',
        'hp_proliant_mem',
        'hp_proliant_power',
        'hp_proliant_psu',
        'hp_proliant_raid',
        'hp_proliant_systeminfo',
        'hp_proliant_temp',
        'hp_sts_drvbox',
        'hr_cpu',
        'hr_fs',
        'hr_ps',
        'if',
        'if64',
        'if64adm',
        'infoblox_osinfo',
        'inv_if',
        'openbsd_sensors',
        'printer_alerts',
        'printer_input',
        'printer_output',
        'printer_pages',
        'printer_supply',
        'pse_poe',
        'qnap_fans',
        'qnap_hdd_temp',
        'quantum_storage_status',
        'snmp_extended_info',
        'snmp_quantum_storage_info',
    }

    for section in agent_based_register.iter_all_snmp_sections():
        for (first_checked_oid, *_rest1), *_rest2 in (  #
                criterion for criterion in section.detect_spec if criterion  #
        ):
            assert (  #
                first_checked_oid.rstrip('.0') in (SYS_DESCR_OID, SYS_OBJID_OID)  #
            ) is (str(section.name) not in known_exceptions)


@pytest.mark.usefixtures("config_load_all_checks")
def test_section_parse_function_does_something():
    """We make sure that the parse function is not trivial

    To ease the learning curve when developing check plugins
    we allow to omit the parse_function (defaulting to labda x: x).

    However this is allmost always a bad idea, so we make sure it
    does not happen in mainline code.
    """

    noop_code = (lambda x: x).__code__.co_code

    legacy_exceptions_for_easier_migration = {
        # snmp sections
        'checkpoint_inv_tunnels',
        'dell_hw_info',
        'hp_proliant_systeminfo',
        'infoblox_osinfo',
        'infoblox_systeminfo',
        'inv_cisco_vlans',
        'juniper_info',
        'snmp_os',
        'snmp_quantum_storage_info',
        # agent sections
        '3ware_disks',
        '3ware_info',
        '3ware_units',
        'ad_replication',
        'aix_lvm',
        'aix_multipath',
        'appdynamics_memory',
        'appdynamics_sessions',
        'appdynamics_web_container',
        'apt',
        'arc_raid_status',
        'arcserve_backup',
        'citrix_controller',
        'citrix_serverload',
        'citrix_sessions',
        'db2_mem',
        'db2_version',
        'dmi_sysinfo',
        'drbd',
        'emcvnx_hwstatus',
        'emcvnx_writecache',
        'esx_vsphere_sensors',
        'filehandler',
        'fsc_ipmi_mem_status',
        'heartbeat_crm',
        'heartbeat_nodes',
        'hivemanager_devices',
        'hpux_cpu',
        'hpux_fchba',
        'hpux_lvm',
        'hpux_multipath',
        'hpux_serviceguard',
        'hyperv_checkpoints',
        'ibm_svc_eventlog',
        'ibm_svc_system',
        'innovaphone_channels',
        'innovaphone_cpu',
        'innovaphone_licenses',
        'innovaphone_mem',
        'innovaphone_temp',
        'ironport_misc',
        'jar_signature',
        'kaspersky_av_quarantine',
        'kaspersky_av_tasks',
        'kaspersky_av_updates',
        'logins',
        'lvm_vgs',
        'mailman_lists',
        'megaraid_bbu',
        'megaraid_pdisks',
        'mongodb_asserts',
        'mongodb_connections',
        'mongodb_flushing',
        'mongodb_instance',
        'mongodb_locks',
        'mounts',
        'mq_queues',
        'msexch_replhealth',
        'msoffice_serviceplans',
        'mssql_versions',
        'netapp_api_cluster',
        'netapp_api_connection',
        'netapp_api_info',
        'netapp_api_status',
        'netapp_api_vf_status',
        'nfsexports',
        'openvpn_clients',
        'oracle_crs_version',
        'oracle_crs_voting',
        'oracle_jobs',
        'oracle_locks',
        'oracle_logswitches',
        'oracle_longactivesessions',
        'oracle_processes',
        'oracle_recovery_area',
        'oracle_recovery_status',
        'oracle_rman_backups',
        'oracle_version',
        'plesk_backups',
        'plesk_domains',
        'qmail_stats',
        'sansymphony_alerts',
        'sansymphony_pool',
        'sansymphony_ports',
        'sansymphony_serverstatus',
        'sap_hana_filesystem',
        'sap_hana_full_backup',
        'sap_hana_mem',
        'sap_hana_process_list',
        'sap_hana_version',
        'sap_state',
        'siemens_plc_cpu_state',
        'solaris_multipath',
        'solaris_prtdiag_status',
        'splunk_alerts',
        'statgrab_cpu',
        'statgrab_load',
        'sylo',
        'symantec_av_progstate',
        'symantec_av_quarantine',
        'symantec_av_updates',
        'timemachine',
        'tsm_drives',
        'tsm_paths',
        'tsm_sessions',
        'ucs_bladecenter_topsystem',
        'unitrends_backup',
        'unitrends_replication',
        'vbox_guest',
        'veeam_jobs',
        'vms_queuejobs',
        'vms_users',
        'vnx_version',
        'vxvm_enclosures',
        'vxvm_multipath',
        'vxvm_objstatus',
        'win_dhcp_pools',
        'windows_broadcom_bonding',
        'windows_multipath',
        'windows_updates',
        'winperf_mem',
        'winperf_msx_queues',
        'winperf_ts_sessions',
        'wmic_process',
        'zerto_vpg_rpo',
        'zpool_status',
        'zypper',
        'dmraid',
        'emcvnx_raidgroups',
        'hpux_tunables',
        'ibm_svc_enclosurestats',
        'ibm_svc_nodestats',
        'ibm_svc_systemstats',
        'j4p_performance',
        'jolokia_metrics',
        'libelle_business_shadow',
        'lsi',
        'msexch_dag',
        'netapp_api_disk',
        'netctr',
        'netif',
        'nvidia',
        'sap',
        'siemens_plc',
        'vms_diskstat',
        'vms_system',
        'winperf',
    }

    for snmp_section in agent_based_register.iter_all_snmp_sections():
        assert (str(snmp_section.name) not in legacy_exceptions_for_easier_migration) is (
            snmp_section.parse_function.__code__.co_code != noop_code)

    for agent_section in agent_based_register.iter_all_agent_sections():
        assert (str(agent_section.name) not in legacy_exceptions_for_easier_migration) is (
            agent_section.parse_function.__code__.co_code != noop_code)
