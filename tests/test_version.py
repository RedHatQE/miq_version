# -*- coding: utf-8 -*-
import pytest

from miq_version import Version, TemplateName

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


@pytest.mark.parametrize(('tmp_name', 'ver_string'),
                         [('miq-nightly-20180531', '20180531'),
                          ('miq-fine-3-20171215', 'fine-3'),
                          ('cfme-58403-20180220', '5.8.4.03')])
def test_template_parsing(tmp_name, ver_string):
    assert TemplateName.parse_template(tmp_name).version == ver_string
