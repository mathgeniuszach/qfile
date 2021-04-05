"""Holds functions for replacing file data or names."""

from . import PathLike, isdir, set_failed

from pathlib import Path
from typing import Union, Iterable

import os
import re


_repl_code = "utf-8"
"""Helper variable for the _repl_* helper functions"""


def _repl_bytes(src: PathLike, old: bytes, new: bytes):
    """Helper function to replace() that replaces bytes in a file"""
    with open(src, "rb") as file:
        data = file.read().replace(old, new)
    with open(src, "wb") as file:
        file.write(data)


def _repl_str(src: PathLike, old: str, new: str):
    """Helper function to replace() that replaces strings in a file"""
    with open(src, "r", encoding=_repl_code) as file:
        data = file.read().replace(old, new)
    with open(src, "w", encoding=_repl_code) as file:
        file.write(data)


def _repl_pattern(src: PathLike, old: re.Pattern, new: str):
    """Helper function to replace() that replaces patterns in a file"""
    with open(src, "r", encoding=_repl_code) as file:
        data = old.sub(new, file.read())
    with open(src, "w", encoding=_repl_code) as file:
        file.write(data)


def replace(src: Union[PathLike, Iterable[PathLike]], old: Union[str, bytes, re.Pattern], new: Union[str, bytes], code: str = "utf-8") -> bool:
    """Replaces all instances of "old" with "new" in the "src" file(s).

    Returns True on complete success and False if there were any errors. If only one file is given, the error would be raised.

    "old" can be a string, a bytes object, or a compiled re.Pattern object.
    If a string or bytes, it is treated literally as exact data to replace.
    If it is a regex object, it will search for that regex in files (in text mode) and replace any matches with the "new" string (which may have indicators like r'\\1', and r'\\2' to denote capture groups). This uses the "Pattern.sub()" function in base python.

    If multiple files are provided in "src", the "failed" list (accessible through failed()) is set to a list of files that could not have their contents replaced.
    """
    global _repl_code
    _repl_code = code

    # Get helper function
    if isinstance(old, bytes):
        # Replace bytes
        if not isinstance(new, bytes):
            raise ValueError(
                "new must be a bytes object if old is a bytes object")
        helper = _repl_bytes
    elif isinstance(old, str):
        # Replace string
        if not isinstance(new, str):
            raise ValueError("new must be a string if old is a string")
        helper = _repl_str
    elif isinstance(old, re.Pattern):
        # Replace pattern
        if not isinstance(new, str):
            raise ValueError("new must be a string if old is a Pattern")
        helper = _repl_pattern
    else:
        raise ValueError("Arguments provided are incorrect")

    # Call helper function on files
    if isinstance(src, (str, os.PathLike)) or not isinstance(src, Iterable):
        helper(src, old, new)
        return True
    else:
        lfailed = []

        for file in src:
            try:
                helper(file, old, new)
            except OSError as e:
                lfailed.append((file, False, e))

        set_failed(lfailed)
        return not bool(lfailed)


# TODO: figure out a better way to rename than os.rename() (which uh, might be hard)
def rename(src: Union[PathLike, Iterable[PathLike]], name: str, regex: Union[str, re.Pattern] = None) -> Union[str, list[str]]:
    """Gives the "src" file/folder(s) the new "name" (including the extension if it is a file). Note that renaming something to a file or folder that already exists will cause an error. Returns a string or list of strings to the paths of the new file names.

    Unlike the os.rename() function, "name" is an exact name and does not include the file path.

    If "regex" is given, it specifies a regex that must matched with in the file name (not including the file path) to replace with "name". "name" will be used as the replacement in the "Pattern.sub" function.

    If multiple files are provided in "src", the "failed" list (accessible through failed()) is set to a list of files and folders that failed to be renamed.
    """
    # Check if name contains invalid characters
    if "/" in name or r"\\" in name:
        raise OSError("replacement name cannot contain any folder separators")

    if regex:
        # Compile regex if necessary
        tregex = regex if isinstance(regex, re.Pattern) else re.compile(regex)

        # If regex object is given, we need to match it on all file names
        if isinstance(src, (str, os.PathLike)) or not isinstance(src, Iterable):
            # Single file with regex
            src_path = Path(src)
            match = tregex.fullmatch(src_path.name)
            if match:
                new_name = src_path.parent.joinpath(match.expand(name))
                os.rename(src_path, new_name)
                return str(new_name)
            else:
                return src
        else:
            # Multiple files with regex
            lfailed = []
            new_names = []

            for file in src:
                try:
                    file_path = Path(file)
                    match = tregex.fullmatch(file_path.name)
                    if match:
                        new_name = file_path.parent.joinpath(
                            match.expand(name))
                        os.rename(file_path, new_name)
                        new_names.append(str(new_name))
                    else:
                        new_names.append(file)
                except OSError as e:
                    lfailed.append((file, isdir(file), e))
                    new_names.append(file)

            set_failed(lfailed)
            return new_names
    else:
        # Otherwise just rename all files to the same name
        if isinstance(src, (str, os.PathLike)) or not isinstance(src, Iterable):
            # Single file without regex
            new_name = Path(src).parent.joinpath(name)
            os.rename(src, new_name)
            return str(new_name)
        else:
            # Multiple files without regex
            lfailed = []
            new_names = []

            for file in src:
                try:
                    new_name = Path(file).parent.joinpath(name)
                    os.rename(file, new_name)
                    new_names.append(new_name)
                except OSError as e:
                    lfailed.append((file, isdir(file), e))
                    new_names.append(file)

            set_failed(lfailed)
            return new_names
