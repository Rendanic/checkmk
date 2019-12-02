# -*- encoding: utf-8
# yapf: disable
checkname = 'oracle_instance'

info = [
    [
        'DB19NA', '19.0.0.0.0', 'OPEN', 'ALLOWED', 'STARTED', '1940',
        '753892746', 'NOARCHIVELOG', 'PRIMARY', 'YES', 'DB19', '261020191253',
        'TRUE', '0', '', '0', '', '', '', '', '-1', ''
    ],
    [
        'DBNOPEN', '19.0.0.0.0', 'MOUNTED', 'ALLOWED', 'STARTED', '1940',
        '753892746', 'ARCHIVELOG', 'PRIMARY', 'YES', 'DB19', '261020191253',
        'FALSE', '0', '', '0', '', '', '', '', '-1', '0'
    ],
    [
        'DBSTBY', '19.0.0.0.0', 'MOUNTED', 'ALLOWED', 'STARTED', '1940',
        '753892746', 'ARCHIVELOG', 'PHYSICAL STANDBY', 'YES', 'DB19',
        '261020191253', 'FALSE', '0', '', '0', '', '', '', '', '-1', '0'
    ],
    [
        'DB19NL', '19.0.0.0.0', 'OPEN', 'ALLOWED', 'STARTED', '1940',
        '753892746', 'ARCHIVELOG', 'PRIMARY', 'YES', 'DB19', '261020191253',
        'FALSE', '0', '', '0', '', '', '', '', '-1', '0'
    ],
    [
        'DB191', '19.0.0.0.0', 'OPEN', 'ALLOWED', 'STARTED', '1940',
        '753892746', 'ARCHIVELOG', 'PRIMARY', 'YES', 'DB19', '261020191253',
        'TRUE', '0', '', '0', '', '', '', '', '-1', '0'
    ],
    [
        'DB191', '19.0.0.0.0', 'OPEN', 'ALLOWED', 'STARTED', '1940',
        '753892746', 'ARCHIVELOG', 'PRIMARY', 'YES', 'DB19', '261020191253',
        'TRUE', '2', 'PDB$SEED', '2527305433', 'READ ONLY', 'NO', '881852416',
        'ENABLED', '1926', '8192'
    ],
    [
        'DB191', '19.0.0.0.0', 'OPEN', 'ALLOWED', 'STARTED', '1940',
        '753892746', 'ARCHIVELOG', 'PRIMARY', 'YES', 'DB19', '261020191253',
        'TRUE', '3', 'ORCL', '3567515271', 'READ WRITE', 'NO', '1010827264',
        'ENABLED', '1925', '8192'
    ]
]

discovery = {
    '': [
        ('DB191', {}), ('DB191.ORCL', {}), ('DB191.PDB$SEED', {}),
        ('DB19NA', {}), ('DB19NL', {}), ('DBNOPEN', {}), ('DBSTBY', {})
    ]
}

checks = {
    '': [
        (
            'DB191', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    0,
                    'CDB Name DB19, Status OPEN, Role PRIMARY, Version 19.0.0.0.0, Up since 2019-12-02 20:54:01 (32 m), Logins allowed, Log Mode archivelog, Force Logging yes',
                    [('uptime', 1940, None, None, None, None)]
                )
            ]
        ),
        (
            'DB191.ORCL', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    0,
                    'PDB Name DB19.ORCL, Status READ WRITE, Up since 2019-12-02 20:54:16 (32 m), PDB Size 964.00 MB',
                    [
                        ('uptime', 1925, None, None, None, None),
                        ('fs_size', 1010827264, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'DB191.PDB$SEED', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    0,
                    'PDB Name DB19.PDB$SEED, Status READ ONLY, Up since 2019-12-02 20:54:15 (32 m), PDB Size 841.00 MB',
                    [
                        ('uptime', 1926, None, None, None, None),
                        ('fs_size', 881852416, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'DB19NA', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    1,
                    'CDB Name DB19, Status OPEN, Role PRIMARY, Version 19.0.0.0.0, Up since 2019-12-02 20:54:01 (32 m), Logins allowed, Log Mode noarchivelog(!)',
                    [('uptime', 1940, None, None, None, None)]
                )
            ]
        ),
        (
            'DB19NL', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    0,
                    'Database Name DB19, Status OPEN, Role PRIMARY, Version 19.0.0.0.0, Up since 2019-12-02 20:54:01 (32 m), Logins allowed, Log Mode archivelog, Force Logging yes',
                    [('uptime', 1940, None, None, None, None)]
                )
            ]
        ),
        (
            'DBNOPEN', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    2,
                    'Database Name DB19, Status MOUNTED(!!), Role PRIMARY, Version 19.0.0.0.0, Up since 2019-12-02 20:54:01 (32 m), Log Mode archivelog, Force Logging yes',
                    [('uptime', 1940, None, None, None, None)]
                )
            ]
        ),
        (
            'DBSTBY', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    0,
                    'Database Name DB19, Status MOUNTED, Role PHYSICAL STANDBY, Version 19.0.0.0.0, Up since 2019-12-02 20:54:01 (32 m), Log Mode archivelog, Force Logging yes',
                    [('uptime', 1940, None, None, None, None)]
                )
            ]
        )
    ]
}
