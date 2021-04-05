"""A python library for simplifying common file operations."""

__maintainer__ = "Zach K"
__version__ = "1.1.0"
__all__ = [
    "default_force", "failed", "uuid", "merge", "clone", "move", "cut", "copy", "a_cut", "a_copy",
    "unmark", "paste", "scan", "glob", "delete", "wd", "folder", "touch", "write", "read",
    "replace", "rename", "exists", "isdir", "isfile", "islink", "parent", "rel", "ftype", "fsize",
    "archive", "extract", "chunks", "lines", "force"
]

# TODO: Add some way of checking the progress of long file operations
# TODO: Support os.symlink without permission issues (currently os.symlink raises an OSError)
# TODO: Add functions of creating in-memory file-trees that can be modified by the same global functions
# TODO: Global or arguements for changing the os "mode" argument of os functions


# Gather some party supplies
from typing import Iterable, Union
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager

import os
import shutil
import threading


PathLike = Union[str, os.PathLike]
"""Type alias for a string or a pathlike object."""

default_force: bool = False
"""Determines the default force mode for the functions in this library (You can specify the "force" parameter on supported function calls to overwrite this setting).

When a function's "force" mode is False, attempts to write/read to folders or make a folder where a file is already will raise an OSError of some kind. When "force" is True, these attempts will instead delete the folder/file and overwrite it with the proper file type. Note that sub-directories are automatically set to force mode.
"""
max_read_size: int = -1
"""Determines the maximum file size in bytes the read() function can handle. Attempting to read from a file larger than this number will cause the read function to raise a ValueError. Set to -1 (default) for no limit."""

_thread_failed: dict[int, list[tuple[PathLike, bool, Exception]]] = {}
"""A dictionary of failed item lists mapped to thread identifiers. Use failed() to access."""


# Renamed functions
exists = os.path.exists
"""This is a direct reference to os.path.exists."""
isdir = os.path.isdir
"""This is a direct reference to os.path.isdir."""
isfile = os.path.isfile
"""This is a direct reference to os.path.isfile."""
islink = os.path.islink
"""This is a direct reference to os.path.islink."""

fsize = os.path.getsize
"""This is a direct reference to os.path.getsize."""
join = os.path.join
"""This is a direct reference to os.path.join."""


def set_failed(failed_list: list):
    """Sets the failed list data for this thread to "failed_list"."""
    _thread_failed[threading.get_ident()] = failed_list


def failed(id: int = None) -> list[tuple[PathLike, bool, Exception]]:
    """Gets the list of failed items from the last function call in this thread, whether or not they are a folder, and the reason they failed. It is safe to work on this returned list and do other function calls because every function call in this library generates a new list.

    There are no guarantees that the first item in each tuple is definitely a string or a Path, only that it is one or the other.

    This function is thread safe and will only grab the latest failed information from the current thread. You can access other thread's failed lists by providing a "thread identifier" (returned by threading.get_ident(), for example).
    """
    sid = threading.get_ident() if id is None else id
    return _thread_failed[sid]


def uuid() -> str:
    """Generates a unique version 4 uuid as a string."""
    return str(uuid4())


def delete(*src: Union[PathLike, Iterable[PathLike]]) -> bool:
    """Deletes the file(s) or folder(s) at "src". Deletes all sub-folders and files. Returns True if completely successful, and False otherwise.

    If a single string is given, returns True if the "src" was deleted or False if "src" does not exist. If a list of strings is given, returns a list of booleans of whether or not the "src" file existed. This function calls itself recusively, so lists of lists of strings are possible too.

    The "failed" list (accessible through failed()) is always set to a list of files and folders that failed, so this function will never raise an OSError.
    """
    lfailed = []

    for item in src:
        if isinstance(item, (str, os.PathLike)) or not isinstance(item, Iterable):
            # Item is not a list
            try:
                # A directory is deleted recursively
                if isdir(item):
                    shutil.rmtree(item)
                # Normal files are deleted normally
                else:
                    os.remove(item)
            except OSError as e:
                lfailed.append((item, isdir(item), e))
        else:
            # Item is a list
            for file in item:
                try:
                    # A directory is deleted recursively
                    if isdir(file):
                        shutil.rmtree(file)
                    # Normal files are deleted normally
                    else:
                        os.remove(file)
                except OSError as e:
                    lfailed.append((file, isdir(file), e))

    set_failed(lfailed)
    return not bool(lfailed)


def parent(child: PathLike) -> Path:
    """Returns the parent of this child element."""
    return Path(child).absolute().parent


def rel(child: PathLike, parent: PathLike) -> Union[Path, None]:
    """Returns the relative path of child in parent as given by Path.relative_to(), or None if "child" is not a child of "parent". Relative paths will be turned into absolute paths.

    For example, If child is "myfolder/thing/that" and parent is "myfolder", this will return Path("thing/that")."""
    try:
        return Path(os.path.abspath(child)).relative_to(os.path.abspath(parent))
    except ValueError:
        return None


def ftype(src: PathLike) -> tuple[Union[None, str], bool]:
    """Returns a string representing the type of the file/folder at "src" and whether or not "src" is a link. The string is either 'file' or 'dir', or None if it does not exist."""
    link = islink(src)
    if isdir(src):
        return 'dir', link
    elif isfile(src):
        return 'file', link
    else:
        return None, link


@contextmanager
def force(force: bool = True):
    """A context manager for temporarily setting the default_force mode. e.g. "with force():" would make all included operations within the "with" block operate under force=True. This will reset "default_force" when the with block finishes."""
    global default_force
    df, default_force = default_force, force
    try:
        yield
    finally:
        default_force = df


def check_force(override: bool = None):
    """Helper method for many sub-modules that returns a boolean value on whether or not force mode is active. Accepts an override."""
    return default_force if override is None else override


def check_size(src: PathLike):
    """Helper method for the file sub-module that checks if a file is too large."""
    return max_read_size > -1 and fsize(src) > max_read_size


# Ok now let everyone know the party's starting
from .archiving import extract, archive
from .clipboard import cut, copy, a_cut, a_copy, unmark, paste
from .file import touch, write, chunks, lines, read
from .dirs import scan, glob, wd, folder
from .relocate import merge, clone, move
from .modify import replace, rename