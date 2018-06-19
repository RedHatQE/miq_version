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
TemplateInfo = namedtuple('TemplateInfo', ['group_name', 'datestamp', 'stream', 'version'])


# Maps stream and product version to each app version
version_stream_product_mapping = {
    '5.2': SPTuple('downstream-52z', '3.0', [
        r'^cfme-(?P<ver>52\d{3})-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-(?P<ver>52\d+)-(?P<month>\d{2})(?P<day>\d{2})',
        r'^docker-(?P<ver>52\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>52)z(-|_)(?P<year>\d{2})?'
        r'(?P<month>\d{2})(?P<day>\d{2})']),
    '5.3': SPTuple('downstream-53z', '3.1', [
        r'^cfme-(?P<ver>53\d{3})-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-(?P<ver>53\d+)-(?P<month>\d{2})(?P<day>\d{2})',
        r'^docker-(?P<ver>53\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>53)z(-|_)(?P<year>\d{2})?'
        r'(?P<month>\d{2})(?P<day>\d{2})']),
    '5.4': SPTuple('downstream-54z', '3.2', [
        r'^cfme-(?P<ver>54\d{3})-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-(?P<ver>54\d+)-(?P<month>\d{2})(?P<day>\d{2})',
        r'^docker-(?P<ver>54\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>54)z(-|_)(?P<year>\d{2})?'
        r'(?P<month>\d{2})(?P<day>\d{2})']),
    '5.5': SPTuple('downstream-55z', '4.0', [
        r'^cfme-(?P<ver>55\d{3})-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-(?P<ver>55\d+)-(?P<month>\d{2})(?P<day>\d{2})',
        r'^docker-(?P<ver>55\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>55)z(-|_)(?P<year>\d{2})?'
        r'(?P<month>\d{2})(?P<day>\d{2})']),
    '5.6': SPTuple('downstream-56z', '4.1', [
        r'^cfme-(?P<ver>56\d{3})-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-nightly-(?P<ver>56\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-(?P<ver>56\d+)-(?P<month>\d{2})(?P<day>\d{2})',
        r'^docker-(?P<ver>56\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>56)z(-|_)(?P<year>\d{2})?'
        r'(?P<month>\d{2})(?P<day>\d{2})']),
    '5.7': SPTuple('downstream-57z', '4.2', [
        r'^cfme-(?P<ver>57\d{3})-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-nightly-(?P<ver>57\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-(?P<ver>57\d+)-(?P<month>\d{2})(?P<day>\d{2})',
        r'^docker-(?P<ver>57\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>57)z(-|_)(?P<year>\d{2})?'
        r'(?P<month>\d{2})(?P<day>\d{2})']),
    '5.8': SPTuple('downstream-58z', '4.5', [
        r'^cfme-(?P<ver>58\d{3})-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-nightly-(?P<ver>58\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-(?P<ver>58\d+)-(?P<month>\d{2})(?P<day>\d{2})',
        r'^docker-(?P<ver>58\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>58)z(-|_)(?P<year>\d{2})?'
        r'(?P<month>\d{2})(?P<day>\d{2})']),
    '5.9': SPTuple('downstream-59z', '4.6', [
        r'^cfme-(?P<ver>59\d{3})-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-nightly-(?P<ver>59\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-(?P<ver>59\d+)-(?P<month>\d{2})(?P<day>\d{2})',
        r'^docker-(?P<ver>59\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>59)z(-|_)(?P<year>\d{2})?'
        r'(?P<month>\d{2})(?P<day>\d{2})']),
    '5.10': SPTuple('downstream-510z', '4.7', [
        r'^cfme-(?P<ver>510\d{3})-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^cfme-(?P<ver>510\d+)-(?P<month>\d{2})(?P<day>\d{2})',
        r'^docker-(?P<ver>510\d+)-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)downstream(-|_)(?P<ver>510)z(-|_)(?P<year>\d{2})?'
        r'(?P<month>\d{2})(?P<day>\d{2})']),
    'darga': SPTuple('upstream-darga', 'master', [
        r'^miq-(?P<ver>darga[-\w]*?)-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
        r'^miq-stable-(?P<ver>darga[-\w]*?)-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)upstream(-|_)(?P<ver>darga[-\w]*?)(-|_)'
        r'(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})']),
    'euwe': SPTuple('upstream-euwe', 'master', [
        r'^miq-(?P<ver>euwe[-\w]*?)-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
        r'^miq-stable-(?P<ver>euwe[-\w]*?)-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)upstream(-|_)(?P<ver>euwe[-\w]*?)(-|_)'
        r'(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})']),
    'fine': SPTuple('upstream-fine', 'master', [
        r'^miq-(?P<ver>fine[-\w]*?)-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
        r'^miq-stable-(?P<ver>fine[-\w]*?)-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)upstream(-|_)(?P<ver>fine[-\w]*?)(-|_)'
        r'(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})']),
    'gap': SPTuple('upstream-gap', 'master', [
        r'^miq-(?P<ver>gapri[-\w]*?)-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
        r'^miq-stable-(?P<ver>gapri[-\w]*?)-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',
        r'^s(-|_)(appl|tpl)(-|_)upstream(-|_)(?P<ver>gapri[-\w]*?)(-|_)'
        r'(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})']),
    LATEST: SPTuple('upstream', 'master', [
        r'miq-nightly-(?P<ver>(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2}))',
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


def futurecheck(check_date):
    """Given a date object, return a date object that isn't from the future

    Some templates only have month/day values, not years. We create a date object

    """
    today = date.today()
    while check_date > today:
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
            match = re.search(
                '^(?P<major>\d)\.?(?P<minor>\d)\.?(?P<patch>\d)\.?(?P<build>\d{1,2})',
                v.content)
            if match:
                return ''.join([match.group('major'),
                                match.group('minor'),
                                match.group('patch'),
                                match.group('build').zfill(2)])  # zero left-pad
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
    def template_name(self):
        """Actually construct the template name"""
        return '-'.join([self.CFME_ID if self.CFME_ID in self.build_url else self.MIQ_ID,
                         self.build_version,
                         self.build_date])

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
                    # validate the template date by turning into a date obj
                    try:
                        # year, month, day might have been parsed incorrectly with loose regex
                        template_date = futurecheck(date(year, month, day))
                    except ValueError:
                        continue
                    if 'downstream' not in stream_tuple.stream:
                        dot_version = version
                    elif version.startswith('51'):
                        version = version.ljust(4, '0')
                        dot_version = '{}.{}.{}.{}'.format(version[0],
                                                           version[1:3],
                                                           version[3],
                                                           version[4:])
                    else:
                        version = version.ljust(4, '0')
                        dot_version = '{}.{}.{}.{}'.format(version[0],
                                                           version[1],
                                                           version[2],
                                                           version[3:])

                    return TemplateInfo(stream_tuple.stream,
                                        template_date,
                                        True,
                                        version=dot_version)
        for group_name, regex in generic_matchers:
            matches = re.match(regex, template_name)
            if matches:
                return TemplateInfo(group_name, None, False, None)
        # If no match, unknown
        return TemplateInfo('unknown', None, False, None)
