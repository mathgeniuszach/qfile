"""Holds functions relating specifically to folders."""

from . import PathLike, isdir, check_force

from pathlib import Path
from typing import Callable, Iterator
from contextlib import contextmanager

import os
import shutil


def _scan_r(src: PathLike, filter: Callable, sfolders: list[PathLike], sfiles: list[PathLike]):
    """Helper function for the scan function."""
    _, folders, files = next(os.walk(src))

    # Get all files
    for file in files:
        absfile = os.path.join(src, file)
        if filter(absfile, False):
            sfiles.append(absfile)
    # Get all folders
    for folder in folders:
        absfolder = os.path.join(src, folder)
        if filter(absfolder, True):
            sfolders.append(absfolder)
            _scan_r(absfolder, filter, sfolders, sfiles)


def scan(src: PathLike, filter: Callable = None, recurse: bool = True) -> tuple[list[str], list[str]]:
    """Scans the folder "src" and returns a tuple of: a list of the absolute paths of all subfolders, and a list of the absolute paths of all files/subfiles. The root folder is not included in the returned folder list.

    Consider using glob() if you want something simpler that yields values instead of generating a full list.

    "filter" is an optional callable that - provided an absolute path to a file/folder and a boolean saying whether or not the item is a folder - returns a boolean determining whether or not to scan/include that file/folder (True to include, False to ignore). Folders that get returned as False are not parsed through.

    By default, this will scan all subfolders too. Set "recurse" to False to disable this behavior.
    """
    if not isdir(src):
        raise NotADirectoryError("src is not a directory")

    sfolders = []
    sfiles = []

    if isinstance(filter, Callable):
        # With a callable we need to do the recursion ourselves
        abspath = os.path.abspath(src)
        _, folders, files = next(os.walk(src))

        # Get all files
        for file in files:
            absfile = os.path.join(abspath, file)
            if filter(absfile, False):
                sfiles.append(absfile)
        # Get all folders
        for folder in folders:
            absfolder = os.path.join(abspath, folder)
            if filter(absfolder, True):
                sfolders.append(absfolder)

        # Recurse through folders
        if recurse:
            for absfolder in sfolders:
                _scan_r(absfolder, filter, sfolders, sfiles)
    else:
        # Simple mode, without a callable
        if recurse:
            for root, folders, files in os.walk(src):
                abspath = os.path.abspath(root)
                # Append folders
                for folder in folders:
                    sfolders.append(os.path.join(abspath, folder))
                # Append files
                for file in files:
                    sfiles.append(os.path.join(abspath, file))
        else:
            abspath = os.path.abspath(src)
            # We only want the root from the generator
            _, folders, files = next(os.walk(src))

            # Append folders
            for folder in folders:
                sfolders.append(os.path.join(abspath, folder))
            # Append files
            for file in files:
                sfiles.append(os.path.join(abspath, file))

    return sfolders, sfiles


def glob(root: PathLike = ".", ptrn: PathLike = "**/*", dirs=True, files=True) -> Iterator[Path]:
    """A wrapper for Path(root).glob(str(ptrn)). Globs over all the folders and files in root.

    This function can automatically check the type of returned paths and filter out directories (folders) or files. Set dirs to False to filter out directories from the returned list, or set dirs to False to filter out files from the returned list. If you set both to False an error will be raised.
    """
    gen = Path(root).glob(str(ptrn))

    if dirs:
        if files:
            # Including both folders and files just means normally globing
            yield from gen
        else:
            # Filter out files but not folders
            for f in gen:
                if not f.is_file():
                    yield f
    else:
        if files:
            # Filter out folders but not files
            for f in gen:
                if not f.is_dir():
                    yield f
        else:
            # Can't filter out both files and folders.
            raise ValueError("cannot filter out both files and folders!")


@contextmanager
def wd(wd, force=None, temp=False):
    """A context manager for temporarily entering a working directory with a with statement. Just use "with wd('working_directory'):". If the working directory does not exist, it will be created automatically. If "temp" is True, the working directory will also be deleted when exiting the "with" block. Failing to delete the temporary directory will not result in an error."""
    owd = os.getcwd()
    try:
        yield folder(wd, cwd=True, force=force)
    finally:
        os.chdir(owd)
        if temp:
            try:
                shutil.rmtree(wd)
            except OSError:
                pass


# TODO: support virtual folders so people can't complain about my naming convention (An in-memory file tree will do fine later on)
def folder(src: PathLike, cwd: bool = False, force=None) -> bool:
    """Creates a folder at "src". Parent folders will be created if they do not exist.

    Setting "cwd" to True will result in changing the working directory to the given "src" folder (regardless of if it was just created or not)

    Returns True if "src" was newly created or False if "src" already exists.
    """
    if isdir(src):
        # If the folder already exists, we don't need to do anything
        # Except of course, enter it as a working directory if necessary
        if cwd:
            os.chdir(src)
        return False
    else:
        if check_force(force):
            # If we are forcing something, we try os.makedirs but if it fails we delete the toxic file
            try:
                os.makedirs(src, exist_ok=True)
            except OSError:
                src_path = Path(src).absolute()
                while not src_path.exists():
                    src_path = src_path.parent
                os.remove(src_path)

                # Retry os.makedirs with the bad file gone (there can only be at most one bad file)
                os.makedirs(src, exist_ok=True)
        else:
            # If we aren't forcing anything, we can use normal os.makedirs
            os.makedirs(src, exist_ok=True)

        # Enter working directory if necessary
        if cwd:
            os.chdir(src)
        return True
