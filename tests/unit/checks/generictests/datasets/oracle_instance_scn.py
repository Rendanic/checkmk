# -*- encoding: utf-8
# yapf: disable
checkname = 'oracle_instance'

info = [
    [
        'DB191', '19.0.0.0.0', 'OPEN', 'ALLOWED', 'STARTED', '67', '753892746',
        'ARCHIVELOG', 'PRIMARY', 'YES', 'DB19', '261020191253', 'TRUE', '0',
        '', '0', '', '', '', '', '-1', '0', '5078504', '20191203200436'
    ]
]

discovery = {'': [('DB191', {})]}

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
                    'CDB Name DB19, Status OPEN, Role PRIMARY, Version 19.0.0.0.0, Up since 2019-12-03 20:17:40 (67 s), Logins allowed, Log Mode archivelog, Force Logging yes, SCN 5078504, 0.00% used SCN Headroom scheme 1',
                    [('uptime', 67, None, None, None, None)]
                )
            ]
        )
    ]
}
