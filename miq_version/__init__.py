import re
from cached_property import cached_property
from collections import namedtuple
from six import string_types


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
            result = self.version < other.version
            if result != 0:
                return result
            # Use suffixes to decide
            if self.suffix is None and other.suffix is None:
                # No suffix, the same
                return 0
            elif self.suffix is None:
                # This does not have suffix but the other does so this is "newer"
                return 1
            elif other.suffix is None:
                # This one does have suffix and the other does not so this one is older
                return -1
            else:
                # Both have suffixes, so do some math
                return self.normalized_suffix < other.normalized_suffix

    def __cmp__(self, other):
        try:
            if not isinstance(other, type(self)):
                other = Version(other)
        except Exception:
            raise ValueError('Cannot compare Version to {}'.format(type(other).__name__))

        if self == other:
            return 0
        elif self == self.latest() or other == self.lowest():
            return 1
        elif self == self.lowest() or other == self.latest():
            return -1
        else:
            result = cmp(self.version, other.version)
            if result != 0:
                return result
            # Use suffixes to decide
            if self.suffix is None and other.suffix is None:
                # No suffix, the same
                return 0
            elif self.suffix is None:
                # This does not have suffix but the other does so this is "newer"
                return 1
            elif other.suffix is None:
                # This one does have suffix and the other does not so this one is older
                return -1
            else:
                # Both have suffixes, so do some math
                return cmp(self.normalized_suffix, other.normalized_suffix)

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

SPTuple = namedtuple('StreamProductTuple', ['stream', 'product_version'])

# Maps stream and product version to each app version
version_stream_product_mapping = {
    '5.2': SPTuple('downstream-52z', '3.0'),
    '5.3': SPTuple('downstream-53z', '3.1'),
    '5.4': SPTuple('downstream-54z', '3.2'),
    '5.5': SPTuple('downstream-55z', '4.0'),
    '5.6': SPTuple('downstream-56z', '4.1'),
    '5.7': SPTuple('downstream-57z', '4.2'),
    '5.8': SPTuple('downstream-58z', '4.5'),
    '5.9': SPTuple('downstream-59z', '4.6'),
    LATEST: SPTuple('upstream', 'master')
}
