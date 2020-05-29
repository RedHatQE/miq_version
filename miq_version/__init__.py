import re
from datetime import date, datetime

import attr
import requests
from cached_property import cached_property
from functools import total_ordering
from lxml import html

from . import constants


@total_ordering
class Version(object):
    """Version class based on distutil.version.LooseVersion"""
    SUFFIXES = ('nightly', 'pre', 'alpha', 'beta', 'rc')
    SUFFIXES_STR = "|".join(rf'-{suffix}(?:\d+(?:\.\d+)?)?' for suffix in SUFFIXES)
    component_re = re.compile(rf'(?:\s*(\d+|[a-z]+|\.|(?:{SUFFIXES_STR})+$))')
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
        if vstring in ('master', 'latest', 'upstream'):
            vstring = 'master'
        for upstream_series in constants.SORTED_UPSTREAM_RELEASES:
            if upstream_series in vstring:
                vstring = upstream_series

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
        return f'{type(self).__name__}({repr(self.vstring)})'

    def __lt__(self, other):
        try:
            if not isinstance(other, type(self)):
                other = Version(other)
        except Exception:
            raise ValueError(f'Cannot compare Version to {type(other).__name__}')

        if self == other:
            return False
        elif self == self.latest() or other == self.lowest():
            return False
        elif self == self.lowest() or other == self.latest():
            return True
        else:
            if self.version != other.version:
                # handle upstream version comparisons
                # This logic might not be the most efficient, but its readable and predictable
                # 1. Both objects are upstream release names, make direct string comparison
                if (self.vstring in constants.SORTED_UPSTREAM_RELEASES and
                        other.vstring in constants.SORTED_UPSTREAM_RELEASES):
                    return self.version < other.version
                # 2. Self is an upstream release name, convert to downstream version number
                elif self.vstring in constants.SORTED_UPSTREAM_RELEASES:
                    # need to compare upstream release string to downstream version
                    map_version = constants.UPSTREAM_DOWNSTREAM_MAPPING.get(self.vstring)
                    return [int(s) for s in map_version.split('.')] < other.version
                # 3. Other is an upstream release name, convert to downstream version number
                elif other.vstring in constants.SORTED_UPSTREAM_RELEASES:
                    # need to compare upstream release string to downstream version
                    map_version = constants.UPSTREAM_DOWNSTREAM_MAPPING.get(other.vstring)
                    return self.version < [int(s) for s in map_version.split('.')]
                else:
                    # handles component list comparison and both versions upstream
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
        for v, spt in constants.version_stream_product_mapping.items():
            if self.is_in_series(v):
                return spt.stream

    def product_version(self):
        for v, spt in constants.version_stream_product_mapping.items():
            if self.is_in_series(v):
                return spt.product_version


LOWEST = Version.lowest()
LATEST = Version.latest()
UPSTREAM = LATEST


def get_version(obj=None):
    """
    Return a Version based on obj.  For CFME, 'master' version
    means always the latest (compares as greater than any other version)

    If obj is None, the version will be retrieved from the current appliance

    """
    if isinstance(obj, Version):
        return obj
    if not isinstance(obj, str):
        obj = str(obj)
    if obj.startswith('master'):
        return Version.latest()
    return Version(obj)


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
    MIQ_ID = 'miq'
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
            match = re.search(constants.VERSION_FORMAT_DOWNSTREAM, v.content.decode('utf-8'))
            if match:
                return '.'.join([match.group('major'),
                                 match.group('minor'),
                                 match.group('patch'),
                                 match.group('build')])
            else:
                raise ValueError(
                    f'Unable to match version string in {self.build_url}/version: {v.content}'
                )
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
                image = images[0]
                match = re.search(constants.BUILD_IMAGE_FORMAT_UPSTREAM, str(image))
                if match:
                    # if its a master image, version is 'nightly', otherwise use release+number
                    return f'{match.group("release")}{match.group("number") or ""}'
                else:
                    raise ValueError(f'Unable to match version string in image file: {image}')
            else:
                raise ValueError(f'No image of expected type found in {self.build_url}')

    @property
    def build_date(self):
        """Get a build date from the SHA256SUM"""
        r = requests.get('/'.join([self.build_url, self.SHA]))
        if r.ok:
            timestamp = datetime.strptime(r.headers.get('Last-Modified'),
                                          "%a, %d %b %Y %H:%M:%S %Z")
            return timestamp.strftime('%Y%m%d')
        else:
            raise ValueError(f'{self.SHA} file not found in {self.build_url}')

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
        for stream_tuple in constants.version_stream_product_mapping.values():
            for regex in stream_tuple.template_regex:
                matches = re.match(regex, template_name)
                if matches:
                    groups = matches.groupdict()
                    # hilarity may ensue if this code is run right before the new year
                    today = date.today()
                    year = int(groups.get('year', today.year) or today.year)
                    month, day = int(groups['month']), int(groups['day'])
                    version = groups.get('ver', '')
                    if (
                        '.' not in version  # the version in the template wasn't dotted
                        and 'downstream' in stream_tuple.stream  # don't try to parse upstream
                        and len(version) > 3
                    ):  # sprout templates only have stream
                        # old template name format with no dots
                        if version.startswith('51'):
                            version = f'{version[0]}.{version[1:3]}.{version[3]}.{version[4:]}'
                        else:
                            version = f'{version[0]}.{version[1]}.{version[2]}.{version[3:]}'

                    # strip - in case regex includes them, replace empty string with None
                    temp_type = groups.get('type') or None
                    # validate the template date by turning into a date obj
                    try:
                        # year, month, day might have been parsed incorrectly with loose regex
                        template_date = datecheck(date(year, month, day))
                    except ValueError:
                        continue

                    return constants.TemplateInfo(
                        stream_tuple.stream,
                        template_date,
                        True,
                        version,
                        temp_type
                    )
        for group_name, regex in constants.generic_matchers:
            matches = re.match(regex, template_name)
            if matches:
                return constants.TemplateInfo(group_name, None, False, None, None)
        # If no match, unknown
        return constants.TemplateInfo('unknown', None, False, None, None)
