# Constants for use in version sorting, comparisons, template naming
# Basic data types

from collections import namedtuple

SPTuple = namedtuple('StreamProductTuple', ['stream', 'product_version', 'template_regex'])
TemplateInfo = namedtuple('TemplateInfo', ['group_name', 'datestamp', 'stream', 'version', 'type'])

FORMATS_DOWNSTREAM = {
    # Looks like: cfme-5.9.3.4-20180531 or cfme-5.10.0.0-pv-20171231
    'template_with_year':
        r'^cfme-'
        r'(?P<ver>(?P<major>{major})\.(?P<minor>{minor})\.(?P<patch>\d+)\.(?P<build>\d+))'
        r'-((?P<type>[\w]*)-)?'
        r'(?P<year>\d{{4}})?(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: cfme-59304-0131
    'template_no_year':
        r'^cfme-(?P<ver>{major}{minor}\d+)-(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: docker-5.8.10.1-20180229
    'template_docker':
        r'^docker-'
        r'(?P<ver>(?P<major>{major})\.?(?P<minor>{minor})\.?(?P<patch>\d+)\.?(?P<build>\d+))'
        r'-(?P<year>\d{{4}})?(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: s_tpl_downstream_59z_20171001 or s-appl-downstream-57z-20161231
    'sprout':
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>{major}{minor})z'
        r'(-|_)(?P<year>\d{{2}})?(?P<month>\d{{2}})(?P<day>\d{{2}})',
}
FORMATS_UPSTREAM = {
    # Looks like: miq-fine-20180531 or miq-euwe-2-20171231
    'upstream_with_year':
        r'^miq-(?P<ver>{stream}[-\w]*?)-(?P<year>\d{{4}})(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: miq-stable-fine-4-20180315
    'upstream_stable':
        r'^miq-stable-(?P<ver>{stream}[-\w]*?)-(?P<year>\d{{4}})(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: s_tpl_upstream_fine-3_20171028 or s-appl-upstream-gapri-20180411
    'upstream_sprout':
        r'^s(-|_)(appl|tpl)(-|_)upstream(-|_)(?P<ver>{stream}[-\w]*?)'
        r'(-|_)(?P<year>\d{{2}})(?P<month>\d{{2}})(?P<day>\d{{2}})'
}
VERSION_FORMAT_DOWNSTREAM = (r'^(?P<major>\d)\.(?P<minor>\d{1,2})\.'
                             r'(?P<patch>\d{1,2})\.(?P<build>\d{1,2})')

# example: manageiq-ovirt-jansa-202005250000-bd09bd05d4.qc2
BUILD_IMAGE_FORMAT_UPSTREAM = (r'manageiq-(?:[\w]+?)-(?P<release>[\w]+?)(?P<number>-\d)?-\d{''3,}')

version_stream_product_mapping = {
    '5.2': SPTuple('downstream-52z', '3.0',
                   [regex.format(major='5', minor='2') for regex in FORMATS_DOWNSTREAM.values()]),
    '5.3': SPTuple('downstream-53z', '3.1',
                   [regex.format(major='5', minor='3') for regex in FORMATS_DOWNSTREAM.values()]),
    '5.4': SPTuple('downstream-54z', '3.2',
                   [regex.format(major='5', minor='4') for regex in FORMATS_DOWNSTREAM.values()]),
    '5.5': SPTuple('downstream-55z', '4.0',
                   [regex.format(major='5', minor='5') for regex in FORMATS_DOWNSTREAM.values()]),
    '5.6': SPTuple('downstream-56z', '4.1',
                   [regex.format(major='5', minor='6') for regex in FORMATS_DOWNSTREAM.values()]),
    '5.7': SPTuple('downstream-57z', '4.2',
                   [regex.format(major='5', minor='7') for regex in FORMATS_DOWNSTREAM.values()]),
    '5.8': SPTuple('downstream-58z', '4.5',
                   [regex.format(major='5', minor='8') for regex in FORMATS_DOWNSTREAM.values()]),
    '5.9': SPTuple('downstream-59z', '4.6',
                   [regex.format(major='5', minor='9') for regex in FORMATS_DOWNSTREAM.values()]),
    '5.10': SPTuple('downstream-510z', '4.7',
                   [regex.format(major='5', minor='10') for regex in FORMATS_DOWNSTREAM.values()]),
    '5.11': SPTuple('downstream-511z', '5.0',
                    [regex.format(major='5', minor='11') for regex in FORMATS_DOWNSTREAM.values()]),
    'euwe': SPTuple('upstream-euwe', 'euwe',
                    [regex.format(stream='euwe') for regex in FORMATS_UPSTREAM.values()]),
    'fine': SPTuple('upstream-fine', 'fine',
                    [regex.format(stream='fine') for regex in FORMATS_UPSTREAM.values()]),
    'gaprindashvili': SPTuple(
        'upstream-gaprindashvili',
        'gaprindashvili',
        [regex.format(stream='gaprindashvili') for regex in FORMATS_UPSTREAM.values()]
    ),
    'hammer': SPTuple('upstream-hammer', 'hammer',
                    [regex.format(stream='hammer') for regex in FORMATS_UPSTREAM.values()]),
    'ivanchuck': SPTuple('upstream-ivanchuck', 'ivanchuck',
                    [regex.format(stream='ivanchuck') for regex in FORMATS_UPSTREAM.values()]),
    'jansa': SPTuple('upstream-jansa', 'jansa',
                    [regex.format(stream='jansa') for regex in FORMATS_UPSTREAM.values()]),
    'master': SPTuple('upstream', 'master',
                    [r'miq-nightly-(?P<ver>(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}))',
                     r'miq-(?P<ver>(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}))',
                     r'^s(-|_)(appl|tpl)(-|_)upstream(-|_)(stable(-|_))?'
                     r'(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})'])
}

UPSTREAM_DOWNSTREAM_MAPPING = {
    'jansa': '5.12',
    'ivanchuck': '5.11',
    'hammer': '5.10',
    'gaprindashvili': '5.9',
    'fine': '5.8',
    'euwe': '5.7'
}


# latest streams, not specific versions
LATEST_DOWN_STREAM = [spt.stream
                     for spt in sorted(version_stream_product_mapping.values(),
                                       key=lambda tup: tup.product_version)
                     if 'downstream' in spt.stream][-1]
SORTED_UPSTREAM_RELEASES = sorted(
    [str(name) for name in UPSTREAM_DOWNSTREAM_MAPPING.keys()],
    reverse=True
)
LATEST_UP_STREAM = SORTED_UPSTREAM_RELEASES[0]

# maps some service templates
generic_matchers = (
    ('sprout', r'^s_tpl'),
    ('sprout', r'^s-tpl'),
    ('sprout', r'^s_appl'),
    ('sprout', r'^s-appl'),
    ('sprout', r'^sprout_template'),
    ('rhevm-internal', r'^raw'),
)
