import re
from datetime import date, datetime

import attr
import requests
from cached_property import cached_property
from collections import namedtuple
from functools import total_ordering
from lxml import html
from six import string_types


@total_ordering
class Version(object):
    """Version class based on distutil.version.LooseVersion"""
    SUFFIXES = ('nightly', 'pre', 'alpha', 'beta', 'rc')
    SUFFIXES_STR = "|".join(r'-{}(?:\d+(?:\.\d+)?)?'.format(suff) for suff in SUFFIXES)
    component_re = re.compile(r'(?:\s*(\d+|[a-z]+|\.|(?:{})+$))'.format(SUFFIXES_STR))
    suffix_item_re = re.compile(r'^([^0-9]+)(\d+(?:\.\d+)?)?$')

    def __init__(self, vstring):
        self.parse(vstring)

    def __hash__(self):
        return hash(self.vstring)

    def parse(self, vstring):
        if vstring is None:
            raise ValueError('Version string cannot be None')
        elif isinstance(vstring, (list, tuple)):
            vstring = ".".join(map(str, vstring))
        elif vstring:
            vstring = str(vstring).strip()
        # TODO separate upstream versions
        if any([
                vstring in ('master', 'latest', 'upstream'),
                'fine' in vstring,
                'euwe' in vstring,
                'gaprindashvili' in vstring]):
            vstring = 'master'
        # TODO These aren't used anywhere - remove?
        if vstring == 'darga-3':
            vstring = '5.6.1'
        if vstring == 'darga-4.1':
            vstring = '5.6.2'
        if vstring == 'darga-5':
            vstring = '5.6.3'

        components = list(filter(lambda x: x and x != '.',
                            self.component_re.findall(vstring)))
        # Check if we have a version suffix which denotes pre-release
        if components and components[-1].startswith('-'):
            self.suffix = components[-1][1:].split('-')    # Chop off the -
            components = components[:-1]
        else:
            self.suffix = None
        for i in range(len(components)):
            try:
                components[i] = int(components[i])
            except ValueError:
                pass

        self.vstring = vstring
        self.version = components

    @cached_property
    def normalized_suffix(self):
        """Turns the string suffixes to numbers. Creates a list of tuples.

        The list of tuples is consisting of 2-tuples, the first value says the position of the
        suffix in the list and the second number the numeric value of an eventual numeric suffix.

        If the numeric suffix is not present in a field, then the value is 0
        """
        numberized = []
        if self.suffix is None:
            return numberized
        for item in self.suffix:
            suff_t, suff_ver = self.suffix_item_re.match(item).groups()
            if suff_ver is None or len(suff_ver) == 0:
                suff_ver = 0.0
            else:
                suff_ver = float(suff_ver)
            suff_t = self.SUFFIXES.index(suff_t)
            numberized.append((suff_t, suff_ver))
        return numberized

    @classmethod
    def latest(cls):
        try:
            return cls._latest
        except AttributeError:
            cls._latest = cls('latest')
            return cls._latest

    @classmethod
    def lowest(cls):
        try:
            return cls._lowest
        except AttributeError:
            cls._lowest = cls('lowest')
            return cls._lowest

    def __str__(self):
        return self.vstring

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, repr(self.vstring))

    def __lt__(self, other):
        try:
            if not isinstance(other, type(self)):
                other = Version(other)
        except Exception:
            raise ValueError('Cannot compare Version to {}'.format(type(other).__name__))

        if self == other:
            return False
        elif self == self.latest() or other == self.lowest():
            return False
        elif self == self.lowest() or other == self.latest():
            return True
        else:
            if self.version != other.version:
                return self.version < other.version
            # Use suffixes to decide
            if self.suffix is None and other.suffix is None:
                # No suffix, the same
                return False
            elif self.suffix is None:
                # This does not have suffix but the other does so this is "newer"
                return False
            elif other.suffix is None:
                # This one does have suffix and the other does not so this one is older
                return True
            else:
                # Both have suffixes, so do some math
                return self.normalized_suffix < other.normalized_suffix

    def __eq__(self, other):
        try:
            if not isinstance(other, type(self)):
                other = Version(other)
            return (
                self.version == other.version and self.normalized_suffix == other.normalized_suffix)
        except Exception:
            return False

    def __contains__(self, ver):
        """Enables to use ``in`` expression for :py:meth:`Version.is_in_series`.

        Example:
            ``"5.5.5.2" in Version("5.5") returns ``True``

        Args:
            ver: Version that should be checked if it is in series of this version. If
                :py:class:`str` provided, it will be converted to :py:class:`Version`.
        """
        try:
            return Version(ver).is_in_series(self)
        except Exception:
            return False

    def is_in_series(self, series):
        """This method checks whether the version belongs to another version's series.

        Eg.: ``Version("5.5.5.2").is_in_series("5.5")`` returns ``True``

        Args:
            series: Another :py:class:`Version` to check against. If string provided, will be
                converted to :py:class:`Version`
        """

        if not isinstance(series, Version):
            series = get_version(series)
        if self in {self.lowest(), self.latest()}:
            if series == self:
                return True
            else:
                return False
        return series.version == self.version[:len(series.version)]

    def series(self, n=2):
        return ".".join(self.vstring.split(".")[:n])

    def stream(self):
        for v, spt in version_stream_product_mapping.items():
            if self.is_in_series(v):
                return spt.stream

    def product_version(self):
        for v, spt in version_stream_product_mapping.items():
            if self.is_in_series(v):
                return spt.product_version


def get_version(obj=None):
    """
    Return a Version based on obj.  For CFME, 'master' version
    means always the latest (compares as greater than any other version)

    If obj is None, the version will be retrieved from the current appliance

    """
    if isinstance(obj, Version):
        return obj
    if not isinstance(obj, string_types):
        obj = str(obj)
    if obj.startswith('master'):
        return Version.latest()
    return Version(obj)


LOWEST = Version.lowest()
LATEST = Version.latest()
UPSTREAM = LATEST

SPTuple = namedtuple('StreamProductTuple', ['stream', 'product_version', 'template_regex'])
TemplateInfo = namedtuple('TemplateInfo', ['group_name', 'datestamp', 'stream', 'version', 'type'])

FORMATS_DOWNSTREAM = {
    # Looks like: cfme-5.9.3.4-20180531 or cfme-5.10.0.0-pv-20171231
    'template_with_year':
        '^cfme-(?P<ver>(?P<major>{major})\.(?P<minor>{minor})\.(?P<patch>\d)\.(?P<build>\d{{1,2}}))'
        '-((?P<type>[\w]*)-)?(?P<year>\d{{4}})?(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: cfme-59304-0131
    'template_no_year':
        '^cfme-(?P<ver>{major}{minor}\d+)-(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: docker-5.8.10.1-20180229
    'template_docker':
        '^docker-'
        '(?P<ver>(?P<major>{major})\.?(?P<minor>{minor})\.?(?P<patch>\d)\.?(?P<build>\d{{1,2}}))'
        '-(?P<year>\d{{4}})?(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: s_tpl_downstream_59z_20171001 or s-appl-downstream-57z-20161231
    'sprout':
        '^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>{major}{minor})z'
        '(-|_)(?P<year>\d{{2}})?(?P<month>\d{{2}})(?P<day>\d{{2}})',
}
FORMATS_UPSTREAM = {
    # Looks like: miq-fine-20180531 or miq-euwe-2-20171231
    'upstream_with_year':
        '^miq-(?P<ver>{stream}[-\w]*?)-(?P<year>\d{{4}})(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: miq-stable-fine-4-20180315
    'upstream_stable':
        '^miq-stable-(?P<ver>{stream}[-\w]*?)-(?P<year>\d{{4}})(?P<month>\d{{2}})(?P<day>\d{{2}})',
    # Looks like: s_tpl_upstream_fine-3_20171028 or s-appl-upstream-gapri-20180411
    'upstream_sprout':
        '^s(-|_)(appl|tpl)(-|_)upstream(-|_)(?P<ver>{stream}[-\w]*?)'
        '(-|_)(?P<year>\d{{2}})(?P<month>\d{{2}})(?P<day>\d{{2}})'
}

# Maps stream and product version to each app version
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
    'darga': SPTuple('upstream-darga', 'master',
                   [regex.format(stream='darga') for regex in FORMATS_UPSTREAM.values()]),
    'euwe': SPTuple('upstream-euwe', 'master',
                    [regex.format(stream='euwe') for regex in FORMATS_UPSTREAM.values()]),
    'fine': SPTuple('upstream-fine', 'master',
                    [regex.format(stream='fine') for regex in FORMATS_UPSTREAM.values()]),
    'gap': SPTuple('upstream-gap', 'master',
                   [regex.format(stream='gapri') for regex in FORMATS_UPSTREAM.values()]),
    LATEST: SPTuple('upstream', 'master',
                    [r'miq-nightly-(?P<ver>(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}))',
                     r'miq-(?P<ver>(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}))',
                     r'^s(-|_)(appl|tpl)(-|_)upstream(-|_)(stable(-|_))?'
                     r'(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})'])
}

# maps some service templates
generic_matchers = (
    ('sprout', r'^s_tpl'),
    ('sprout', r'^s-tpl'),
    ('sprout', r'^s_appl'),
    ('sprout', r'^s-appl'),
    ('sprout', r'^sprout_template'),
    ('rhevm-internal', r'^raw'),
)


def datecheck(check_date):
    """Given a date object, return a date object that isn't from the future or distant past

    Some templates only have month/day values, not years. We create a date object
    Some templates have a timestamp that ends up parsing to a yyyymmdd
        But they were actually HHMMmmdd, like 11221212, dec 12th 11:22 AM, not dec 12 year 1122
        Make sure the date isn't from future, but is also within the last 10 years

    """
    today = date.today()
    # long ago, or at least start of the millennium
    if check_date.year < 100:
        # 2 digit year, add millenia
        check_date = check_date.replace(year=check_date.year + 2000)
    elif check_date.year < 2000:
        # probably parsed wrong from an HHMMmmdd (hour-minute-month-day) timestamp, reset year
        check_date = check_date.replace(year=today.year)
    while check_date > today:
        # keep walking back, don't just set year, because month/day might be later in the year
        check_date = date(check_date.year - 1, check_date.month, check_date.day)
    return check_date


@attr.s
class TemplateName(object):
    """Generate a template name from given link, using build timestamp

    This method should handle naming templates from the following URL types:

    - http://<build-server-address>/builds/manageiq/master/latest/
    - http://<build-server-address>/builds/manageiq/gaprindashvili/stable/
    - http://<build-server-address>/builds/manageiq/fine/stable/
    - http://<build-server-address>/builds/cfme/5.8/stable/
    - http://<build-server-address>/builds/cfme/5.9/latest/

    These builds fall into a few categories:

    - MIQ nightly (master/latest)  (upstream)
    - MIQ stable (<name>/stable)  (upstream_gap, upstream_fine, etc)
    - CFME nightly (<stream>/latest)  (downstream-nightly)
    - CFME stream (<stream>/stable)  (downstream-<stream>)

    The generated template names should follow the syntax with 5 digit version numbers:

    - MIQ nightly: miq-nightly-<yyyymmdd>  (miq-nightly-201711212330)
    - MIQ stable: miq-<name>-<number>-yyyymmdd  (miq-fine-4-20171024, miq-gapri-20180130)
    - CFME stream: cfme-<version>-<yyyymmdd>  (cfme-57402-20171202)

    Release names for upstream will be truncated to 5 letters (thanks gaprindashvili...)
    """
    SHA = 'SHA256SUM'
    CFME_ID = 'cfme'
    MIQ_ID = 'manageiq'
    build_url = attr.ib()  # URL to the build folder with ova/vhd/qc2/etc images
    # specific image URL, when set the template name will include build type info, like paravirtual
    image_url = attr.ib(default=None)

    @property
    def build_version(self):
        """Version string from version file in build folder (cfme)
        release name and build number from an image file (MIQ)

        Will substitute 'nightly' for master URLs

        Raises:
            ValueError if unable to parse version string or release name from files

        Returns:
            String 5-digit version number or release name for MIQ
        """
        v = requests.get('/'.join([self.build_url, 'version']))
        if v.ok:
            # split and reform version string to be explicit and verbose+
            match = re.search(
                '^(?P<major>\d)\.(?P<minor>\d{1,2})\.(?P<patch>\d{1,2})\.(?P<build>\d{1,2})',
                v.content)
            if match:
                return '.'.join([match.group('major'),
                                 match.group('minor'),
                                 match.group('patch'),
                                 match.group('build')])
            else:
                raise ValueError('Unable to match version string in %s/version: {}'
                                 .format(self.build_url, v.content))
        else:
            build_dir = requests.get(self.build_url)
            link_parser = html.fromstring(build_dir.content)
            # Find image file links, use first one to pattern match name
            # iterlinks returns tuple of (element, attribute, link, position)
            images = [l
                      for _, a, l, _ in link_parser.iterlinks()
                      if a == 'href' and l.endswith('.ova') or l.endswith('.vhd')]
            if images:
                # pull release and its possible number (with -) from image string
                # examples: miq-prov-fine-4-date-hash.vhd, miq-prov-gaprindashvilli-date-hash.vhd
                match = re.search(
                    'manageiq-(?:[\w]+?)-(?P<release>[\w]+?)(?P<number>-\d)?-\d{''3,}',
                    str(images[0]))
                if match:
                    # if its a master image, version is 'nightly', otherwise use release+number
                    return ('nightly'
                            if 'master' in match.group('release')
                            else '{}{}'.format(match.group('release')[:5], match.group('number')))
                else:
                    raise ValueError('Unable to match version string in image file: {}'
                                     .format(images[0]))
            else:
                raise ValueError('No image of ova or vhd type found to parse version from in {}'
                                 .format(self.build_url))

    @property
    def build_date(self):
        """Get a build date from the SHA256SUM"""
        r = requests.get('/'.join([self.build_url, self.SHA]))
        if r.ok:
            timestamp = datetime.strptime(r.headers.get('Last-Modified'),
                                          "%a, %d %b %Y %H:%M:%S %Z")
            return timestamp.strftime('%Y%m%d')
        else:
            raise ValueError('{} file not found in {}'.format(self.SHA, self.build_url))

    @property
    def build_type(self):
        """Get a specific template type from the image URL
        Used for things like vpshere where there is separate paravirtual image
        Or rhv, where there are ova and qcow2 images

        Only set if a specific image url was supplied for the object, not applicable when looking at
        an entire build directory of images.
        """
        if not self.image_url:
            return None
        elif 'paravirtual' in self.image_url:
            return 'pv'
        else:
            return self.image_url.split('.')[-1]  # file type

    @property
    def template_name(self):
        """Actually construct the template name"""
        name_args = [self.CFME_ID if self.CFME_ID in self.build_url else self.MIQ_ID,
                     self.build_version]
        bt = self.build_type
        if bt:
            name_args.append(bt)
        name_args.append(self.build_date)

        return '-'.join(name_args)

    @classmethod
    def parse_template(cls, template_name):
        """Given a template name, attempt to extract its group name and upload date

            Returns:
                * None if no groups matched
                * group_name, datestamp of the first matching group. group name will be a string,
                  datestamp with be a :py:class:`datetime.date <python:datetime.date>`, or None if
                  a date can't be derived from the template name
            """
        for stream_tuple in version_stream_product_mapping.values():
            for regex in stream_tuple.template_regex:
                matches = re.match(regex, template_name)
                if matches:
                    groups = matches.groupdict()
                    # hilarity may ensue if this code is run right before the new year
                    today = date.today()
                    year = int(groups.get('year', today.year) or today.year)
                    month, day = int(groups['month']), int(groups['day'])
                    version = groups.get('ver')
                    if ('.' not in version and  # the version in the template wasn't dotted
                            'downstream' in stream_tuple.stream and  # don't try to parse upstream
                            len(version) > 3):  # sprout templates only have stream
                        # old template name format with no dots
                        if version.startswith('51'):
                            version = '{}.{}.{}.{}'.format(version[0],
                                                           version[1:3],
                                                           version[3],
                                                           version[4:])
                        else:
                            version = '{}.{}.{}.{}'.format(version[0],
                                                           version[1],
                                                           version[2],
                                                           version[3:])

                    # strip - in case regex includes them, replace empty string with None
                    temp_type = groups.get('type') or None
                    # validate the template date by turning into a date obj
                    try:
                        # year, month, day might have been parsed incorrectly with loose regex
                        template_date = datecheck(date(year, month, day))
                    except ValueError:
                        continue

                    return TemplateInfo(stream_tuple.stream,
                                        template_date,
                                        True,
                                        version,
                                        temp_type)
        for group_name, regex in generic_matchers:
            matches = re.match(regex, template_name)
            if matches:
                return TemplateInfo(group_name, None, False, None, None)
        # If no match, unknown
        return TemplateInfo('unknown', None, False, None, None)
