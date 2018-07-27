# -*- coding: utf-8 -*-
import pytest
from datetime import date

from deepdiff import DeepDiff

from miq_version import Version, TemplateName, datecheck, TemplateInfo

TODAY = date.today()

version_list = [
    Version('5.7.0.0'),
    Version('5.7.0.11-rc1'),
    Version('5.7.0.5-alpha2'),
    Version('5.7.0.17-nightly'),
    Version('5.7.0.6-alpha3'),
    Version('5.7.0.12-rc2'),
    Version('5.7.0.1'),
    Version('5.7.0.6'),
    Version('5.7.0.5'),
    Version('5.7.0.4'),
    Version('5.7.0.9'),
    Version('5.7.0.2'),
    Version('5.7.0.10-beta3'),
    Version('5.7.0.13-rc3'),
    Version('5.7.0.3'),
    Version('5.7.0.7-beta1'),
    Version('5.7.1.3'),
    Version('5.7.1.0'),
    Version('5.7.1.1'),
    Version('5.7.4.3'),
    Version('5.7.4.2'),
    Version('5.7.4.1'),
    Version('5.7.4.0'),
    Version('5.7.2.1'),
    Version('5.7.2.0'),
    Version('5.7.3.2'),
    Version('5.7.1.2'),
    Version('5.7.0.17'),
    Version('5.7.0.16'),
    Version('5.7.0.14'),
    Version('5.7.0.13'),
    Version('5.7.0.11'),
    Version('5.7.0.10'),
    Version('5.7.0.14-rc4'),
    Version('5.7.3.1'),
    Version('5.7.0.9-beta2.1'),
    Version('5.7.0.7'),
    Version('5.7.0.4-alpha1'),
    Version('5.7.3.0'),
    Version('5.7.0.12')
]

reverse_sorted_version = [
    Version('5.7.4.3'),
    Version('5.7.4.2'),
    Version('5.7.4.1'),
    Version('5.7.4.0'),
    Version('5.7.3.2'),
    Version('5.7.3.1'),
    Version('5.7.3.0'),
    Version('5.7.2.1'),
    Version('5.7.2.0'),
    Version('5.7.1.3'),
    Version('5.7.1.2'),
    Version('5.7.1.1'),
    Version('5.7.1.0'),
    Version('5.7.0.17'),
    Version('5.7.0.17-nightly'),
    Version('5.7.0.16'),
    Version('5.7.0.14'),
    Version('5.7.0.14-rc4'),
    Version('5.7.0.13'),
    Version('5.7.0.13-rc3'),
    Version('5.7.0.12'),
    Version('5.7.0.12-rc2'),
    Version('5.7.0.11'),
    Version('5.7.0.11-rc1'),
    Version('5.7.0.10'),
    Version('5.7.0.10-beta3'),
    Version('5.7.0.9'),
    Version('5.7.0.9-beta2.1'),
    Version('5.7.0.7'),
    Version('5.7.0.7-beta1'),
    Version('5.7.0.6'),
    Version('5.7.0.6-alpha3'),
    Version('5.7.0.5'),
    Version('5.7.0.5-alpha2'),
    Version('5.7.0.4'),
    Version('5.7.0.4-alpha1'),
    Version('5.7.0.3'),
    Version('5.7.0.2'),
    Version('5.7.0.1'),
    Version('5.7.0.0')
]

GT = '>'
LT = '<'
EQ = '=='


@pytest.mark.parametrize(('v1', 'op', 'v2'), [
    ('1', LT, '2'),
    ('1', EQ, '1'),
    ('1.2.3.4', LT, '1.2.3.4.1'),
    ('1.2.3.4.1', GT, '1.2.3.4'),
    # (1.1, EQ, '1.1'),
    # (1, EQ, '1'),
    ('5.7.0.23', GT, '5.7.0.21'),
    ('1.2.3.4-beta', LT, '1.2.3.4'),
    ('1.2.3.4-beta1', GT, '1.2.3.4-beta'),
    ('1.2.3.4-beta1.1', GT, '1.2.3.4-beta1'),
    ('1.2.3.4-alpha-nightly', GT, '1.2.3.4-alpha')])  # TODO: This one might be discussed
def test_version(v1, op, v2):
    v1 = Version(v1)
    v2 = Version(v2)
    if op == GT:
        assert v1 > v2
        # exercise
        assert v1 >= v2
    elif op == LT:
        assert v1 < v2
        # exercise
        assert v1 <= v2
    elif op == EQ:
        assert v1 == v2
        # to exercise all
        assert v1 <= v2
        assert v1 >= v2


def test_version_list():
    assert sorted(version_list, reverse=True) == reverse_sorted_version


# namedtuple('TemplateInfo', ['group_name', 'datestamp', 'stream', 'version', 'type'])
@pytest.mark.parametrize(
    ('tmp_name', 'info_tuple'), [
        ('cfme-51006-07252250',  # older format
         TemplateInfo('downstream-510z', date(2018, 7, 25), True, '5.10.0.6', None)),
        ('cfme-59410-04132250',  # older format, might break eventually because of year not present
         TemplateInfo('downstream-59z', date(2018, 4, 13), True, '5.9.4.10', None)),
        ('miq-nightly-20180531',
         TemplateInfo('upstream', date(2018, 5, 31), True, '20180531', None)),
        ('miq-darga-20151009',
         TemplateInfo('upstream-darga', date(2015, 10, 9), True, 'darga', None)),
        ('miq-euwe-20161028',
         TemplateInfo('upstream-euwe', date(2016, 10, 28), True, 'euwe', None)),
        ('miq-fine-3-20171215',
         TemplateInfo('upstream-fine', date(2017, 12, 15), True, 'fine-3', None)),
        ('miq-gapri-20180411',
         TemplateInfo('upstream-gap', date(2018, 4, 11), True, 'gapri', None)),
        ('cfme-5.2.5.3-20180213',
         TemplateInfo('downstream-52z', date(2018, 2, 13), True, '5.2.5.3', None)),
        ('cfme-5.3.5.03-20180213',
         TemplateInfo('downstream-53z', date(2018, 2, 13), True, '5.3.5.03', None)),
        ('cfme-5.4.5.3-20180213',
         TemplateInfo('downstream-54z', date(2018, 2, 13), True, '5.4.5.3', None)),
        ('cfme-5.5.5.3-20180213',
         TemplateInfo('downstream-55z', date(2018, 2, 13), True, '5.5.5.3', None)),
        ('cfme-5.6.5.3-20180213',
         TemplateInfo('downstream-56z', date(2018, 2, 13), True, '5.6.5.3', None)),
        ('cfme-5.7.5.3-20180213',
         TemplateInfo('downstream-57z', date(2018, 2, 13), True, '5.7.5.3', None)),
        ('cfme-5.8.4.3-20180220',
         TemplateInfo('downstream-58z', date(2018, 2, 20), True, '5.8.4.3', None)),
        ('cfme-5.10.0.3-20180221',
         TemplateInfo('downstream-510z', date(2018, 2, 21), True, '5.10.0.3', None)),
        ('cfme-5.10.1.10-20180222',
         TemplateInfo('downstream-510z', date(2018, 2, 22), True, '5.10.1.10', None)),
        ('cfme-5.9.3.10-pv-20180223',
         TemplateInfo('downstream-59z', date(2018, 2, 23), True, '5.9.3.10', 'pv')),
        ('cfme-5.9.4.1-qcow2-20180224',
         TemplateInfo('downstream-59z', date(2018, 2, 24), True, '5.9.4.1', 'qcow2')),
        ('docker-59410-20180606',
         TemplateInfo('downstream-59z', date(2018, 6, 6), True, '5.9.4.10', None)),
        ('docker-5.9.4.10-20180606',
         TemplateInfo('downstream-59z', date(2018, 6, 6), True, '5.9.4.10', None)),
        ('s_tpl_downstream-510z_180621_nBAFLQ8A',
         TemplateInfo('downstream-510z', date(2018, 6, 21), True, '510', None))]
)
def test_template_parsing(tmp_name, info_tuple):
    parsed = TemplateName.parse_template(tmp_name)
    print('template name: {}'.format(tmp_name))
    print('Parsed template: {}'.format(parsed))
    print('expected: {}'.format(info_tuple))
    diff = DeepDiff(parsed, info_tuple,
                    verbose_level=0,  # If any higher, will flag string vs unicode
                    ignore_order=False)
    assert diff == {}


@pytest.mark.parametrize(
    ('image_url', 'expected_type'),
    [('http://domain.example.com/build/folder/path/cfme-5.9.1.1-paravirtual.ova', 'pv'),
     ('http://domain.example.com/build/folder/path/cfme-5.9.1.1.qcow2', 'qcow2')])
def test_template_build_type(image_url, expected_type):
    """test the build_type parameter of TemplateName class

    Bogus build_url, only image_url is used for this property

    TODO: mock requests for testing other parameters of TemplateName
    """
    t = TemplateName(build_url='http://fake.example.com', image_url=image_url)
    assert t.build_type == expected_type


@pytest.mark.parametrize(
    ('test_date', 'expected_date'),
    [(date(2018, 1, 1), date(2018, 1, 1)),
     (date(2000, TODAY.month, TODAY.day), date(2000, TODAY.month, TODAY.day)),  # past, no modify
     (date(1999, TODAY.month, TODAY.day), date(2018, TODAY.month, TODAY.day)),  # past, modified
     (date(16, TODAY.month, TODAY.day), date(2016, TODAY.month, TODAY.day)),  # short year
     (date(30, TODAY.month, TODAY.day), date(2018, TODAY.month, TODAY.day)),  # short year, future
     (date(1130, TODAY.month, TODAY.day), date(TODAY.year, TODAY.month, TODAY.day)),  # bad parse
     (date(2019, TODAY.month, TODAY.day), date(2018, TODAY.month, TODAY.day)),  # future, 1 year
     (date(2030, TODAY.month, TODAY.day), date(2018, TODAY.month, TODAY.day))])  # future, iterate
def test_datecheck(test_date, expected_date):
    assert expected_date == datecheck(test_date)
