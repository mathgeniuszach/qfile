"""Holds functions for cut-copy-pasting folders around."""

from . import PathLike, isdir, rel, failed, set_failed
from .relocate import move, clone

from typing import Iterable, Union
from pathlib import Path

import os


_cut_files: list[PathLike] = []
"""Files internally marked for being moved on call to paste()."""
_copied_files: list[PathLike] = []
"""Files internally marked for being copies on call to paste()."""


def cut(*src: Union[PathLike, Iterable[PathLike]]):
    """Marks a set of files and folders to be moved by paste(). Clears any marked files/folders."""
    unmark()
    a_cut(src)


def copy(*src: Union[PathLike, Iterable[PathLike]]):
    """Marks a set of files and folders to be copied by paste(). Clears any marked files/folders."""
    unmark()
    a_copy(src)


def a_cut(*src: Union[PathLike, Iterable[PathLike]]):
    """Works like cut() but doesn't unmark any already marked files/folders."""
    for item in src:
        if isinstance(item, (str, os.PathLike)) or not isinstance(item, Iterable):
            _cut_files.append(item)
        else:
            _cut_files.extend(item)


def a_copy(*src: Union[PathLike, Iterable[PathLike]]):
    """Works like copy() but doesn't unmark any already marked files/folders."""
    for item in src:
        if isinstance(item, (str, os.PathLike)) or not isinstance(item, Iterable):
            _copied_files.append(item)
        else:
            _copied_files.extend(item)


def unmark():
    """Unmarks all marked files and folders."""
    _cut_files.clear()
    _copied_files.clear()


_paste_info = [(move, _cut_files), (clone, _copied_files)]
"""Info for the paste function."""


def paste(dst: PathLike, root: PathLike = None, force=None) -> bool:
    """Pastes (moves or copies) a set of files and folders into the folder "dst". All marked items will become unmarked. Non-existant marked items will be ignored. Returns True on complete success, and False on failure.

    Note that

    By default, the copied folders and files do not keep their parent folder structure. If "root" is provided, any marked folders and files found in the folder "root" are copied into "dst" with their folder structure under "root" ("root" is not included). Every other folder or file is copied into dst normally.

    The "failed" list (accessed through failed()) is set to a list of files and folders that failed.
    """
    lfailed = []

    if root is None:
        # Move/Clone files normally as root does not exist
        for helper, files in _paste_info:
            for file in files:
                try:
                    helper(file, dst, into=True, force=force)
                    lfailed.extend(failed())
                except OSError as e:
                    lfailed.append((file, isdir(), e))
    else:
        # Root exists, so the steps are a little bit harder
        root_path = Path(root)
        # Move/Clone files
        for helper, files in _paste_info:
            for file in files:
                try:
                    # Move/Clone into given folder
                    rel_path = rel(file, root_path)
                    if rel_path:
                        # If file is in root
                        helper(file, os.path.join(dst, rel_path.parent),
                               into=True, force=force)
                    else:
                        # File is not in root
                        helper(file, dst, into=True, force=force)
                    lfailed.extend(failed())
                except OSError as e:
                    lfailed.append((file, isdir(), e))

    set_failed(lfailed)
    unmark()
