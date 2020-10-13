"""
ansible.module_utils.dotdiff generates nested diffs using dot-path notation.

:authors: Timo Beckers
:license: MIT
"""
import itertools


class Undefined(object):
    """
    Undefined is a dummy object.

    It is used to explicitly indicate that a dictionary key is missing on
    either side of a diff entry. This is required because all basic Python data
    types can be encoded in json, which is our primary conversion format. There
    is no other easy way to check the difference between a null (None) value or
    a missing dict key using get(). Undefined is inspired by jinja2's
    implementation.
    """

    pass


class DiffEntry(object):
    """
    DiffEntry is a representation of a difference.

    It describes the attribute's key (path) and its values on both sides of
    the structure.
    """

    def __init__(self, path=list(), old=None, new=None):
        """Initialize a new DiffEntry."""
        self.path = path
        self.old = old
        self.new = new

        # Visual representation of a missing key in a dictionary
        self.undef_str = '<undefined>'

    def __repr__(self):
        """Represent the DiffEntry in human-readable format."""
        old = self.undef_str if self.old is Undefined else self.old
        new = self.undef_str if self.new is Undefined else self.new

        return '{path}: "{old}" => "{new}"'.format(path='.'.join(self.path), old=old, new=new)


def _ltod(ilist):
    """Convert a list to an str(int)-indexed dictionary."""
    return {str(i): v for i, v in enumerate(ilist)}


def _get_path(diff_entry):
    """
    Return the 'path' attribute of a DiffEntry.

    Used in the sort function.
    """
    return diff_entry.path


def dotdiff(old, new, prefix=list()):
    """
    Find the different between two nested structures, visualizing each change.

    Path logging idea inspired by an answer in
    https://stackoverflow.com/questions/11929904/traverse-a-nested-dictionary-and-get-the-path-in-python
    """
    # Initialize the 'old' parameter to the same type as 'new' if it's undefined
    # This allows for the 'old' parameter to be undefined without causing the algorithm
    # to treat it as a simple value. (no recursive call, no path diffs)
    if old in (Undefined, None) and new not in (Undefined, None):
        old = type(new)()
    # Likewise, if new is Undefined or None, consider the new value of the same
    # type as the old one.
    elif new in (Undefined, None) and old not in (Undefined, None):
        new = type(old)()

    # Ensure both values are of the same type when there are no None values.
    if type(old) != type(new):
        raise Exception('Requested a diff of a {} (original) and a {} (target), aborting.'.format(
            type(old), type(new)))

    diff = []
    keys = []

    # Check if we're comparing lists, in which case we convert the list to a
    # dictionary with keys corresponding to their indexes like '0', '1', '2'.
    # This greatly simplifies the code ahead, since we only ever have to compare
    # dictionaries, and get() can be used on them.
    if isinstance(new, list) and isinstance(old, list):

        newl = new
        oldl = old

        # Convert lists to int-indexed dictionaries
        new = _ltod(new)
        old = _ltod(old)

        # Cardinality indicator
        # Virtual diff entry ending with a pound sign, indicating a difference in the amount
        # of members in a list or dictionary.
        if len(newl) != len(oldl):
            # Entry describing a change in the amount of entries in a list
            count_prefix = prefix[:]
            count_prefix.append('#')

            diff.append(DiffEntry(path=count_prefix,
                                  old=len(old), new=len(new)))

        # When comparing lists, all keys (old and new) are compared; values can be added, removed
        # or changed on both sides. Both old and new keys are converted to a set to remove dupes.
        # This yields a unique list of keys that we can try and compare between both sets, like:
        # hosts.1: "foodomain" => "<undefined>"
        keys = itertools.chain(new.keys(), old.keys())

    elif isinstance(new, dict) and isinstance(old, dict):
        # When comparing dicts, we only consider diffing keys set in the target dictionary.
        # This allows the user to omit default values from the document.
        keys = new.keys()

    else:
        # Only diff nested structures
        raise Exception('dotdiff() can only diff nested structures (got a {} and a {})'.format(
            type(old), type(new)))

    # Traverse the dictionary on the left, and report values that are missing or changed on the right.
    for ikey in keys:

        # Make a copy of upstream prefix
        local_prefix = prefix[:]
        local_prefix.append(ikey)

        # Extract values. Missing keys will be the special object 'Undefined'
        oldv = old.get(ikey, Undefined)
        newv = new.get(ikey, Undefined)

        if oldv != newv:
            # Found a value difference
            if isinstance(newv, dict) or isinstance(newv, list):
                # Recurse into the nested structure
                diff.extend(dotdiff(oldv, newv, prefix=local_prefix))
            else:
                # Return a simple diff entry with the path and the two values
                diff.append(DiffEntry(path=local_prefix, old=oldv, new=newv))

    # Return list sorted by DiffEntry's path
    return sorted(diff, key=_get_path)

