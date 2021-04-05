"""Holds functions for moving, cloning, or merging things."""

from . import PathLike, isdir, isfile, exists, set_failed, rel, uuid, parent
from .dirs import folder

from pathlib import Path

import qfile
import os
import shutil


def merge(src: PathLike, dst: PathLike, move=False, force=None) -> bool:
    """Copies "src" into "dst". All existing sub-folders in "src" will be copied too, and all existing files in "dst" will be overwritten (except folders where files should be and vice-versa). Files and folders in "dst" that don't exist in "src" are untouched. Unlike other functions which make the parent folders themselves, "src" and "dst" need to exist for this function to work.

    If "dst" is a parent of "src", "src" is moved out of "dst" first and afterwards merged into "dst". if "src" and "dst" are the same, this function does nothing to that folder. If "src" is a parent of "dst", this function will raise an error.

    Returns True on complete success, and False if any errors occurred.

    If "move" is True, files will be moved into the new directory instead of copied.

    NOTE: normally you will want to use clone() or move() instead of this function as they will create "dst" for you.

    Sets the "failed" list (accessible through failed()) to a list of failed folder/file names and their reason for failure.
    """
    # Check if src and dst directories are valid
    if not isdir(src):
        raise NotADirectoryError("src is not a directory")
    if not isdir(dst):
        raise NotADirectoryError("dst is not a directory")
    if os.path.abspath(src) == os.path.abspath(dst):
        # A folder does not need to be merged into itself
        return
        # raise shutil.SameFileError("src and dst directories are the same")

    lfailed = []
    rforce = qfile.default_force if force is None else force

    helper = shutil.move if move else shutil.copy

    # If dst is a parent of src, we temporarily move src out of dst
    # TODO: really think about whether or not this is necessary, or if it can be done in-place instead
    rel_dst = rel(src, dst)
    if rel_dst:
        # Find a unique place to temp move to
        src_path = Path(dst).with_name(uuid())
        # Move to that unique place
        shutil.move(src, src_path)
        # src_path is already set to the new location so it can be merged
        walker = os.walk(src_path)
    else:
        # Necessary for below for-loop
        src_path = Path(src)

        if rel(dst, src):
            # If "dst" is in "src", we throw an error.
            raise PermissionError("dst is inside src folder")
            # if move:
            #     # Moving a folder into itself is illegal; but
            # else:
            #     # If dst is in src, we need to generate the list of files in memory to copy first so there's no recursion issues
            #     # TODO: Figure out a better way of doing this
            #     walker = list(os.walk(src))
        else:
            walker = os.walk(src)

    # TODO: If it's faster, custom-recurse so that if a folder doesn't exist in dst we can take a shortcut and rename/copytree it instead of going through it's sub-files and folders
    for folder, _, files in walker:
        try:
            rel_folder = Path(folder).relative_to(src_path)
            # Get dst root path
            dst_folder = os.path.join(dst, rel_folder)

            # Ensure folder exists
            if not isdir(dst_folder):
                if rforce and isfile(dst_folder):
                    os.remove(dst_folder)
                os.mkdir(dst_folder)

            # Copy/Move all files over
            for file in files:
                # Get root paths
                src_file = os.path.join(folder, file)
                dst_file = os.path.join(dst_folder, file)

                try:
                    # Ensure this file is not gonna go into a directory
                    if isdir(dst_file):
                        if not rforce:
                            raise FileExistsError(
                                "cannot copy file where a directory is")
                        shutil.rmtree(dst_file)

                    # Copy/Move file over
                    helper(src_file, dst_file)

                except OSError as e:
                    lfailed.append((src_file, False, e))

        except OSError as e:
            lfailed.append((folder, True, e))

        # If moving, delete leftover folders
        if move:
            shutil.rmtree(src_path)
        elif rel_dst:
            # If cloning and src in dst, we now need to move in the opposite direction
            if exists(src):
                merge(src_path, src, move=True, force=force)
            else:
                _move(src_path, Path(src))

    set_failed(lfailed)
    return not bool(lfailed)


def clone(src: PathLike, dst: PathLike, into: bool = False, force=None) -> str:
    """Clones a file or folder to the destination "dst". Returns the path of the file or folder clone.

    By default, "dst" is the path of the new file or folder, including the extension; if "into" is True, "dst" is treated as a folder (not a file name) to clone the file or folder into. Parent folders will be created if they do not exist. If "dst" already exists, it will be overwritten or merged into. This function will throw an error if "src" is a folder parent of "dst".

    Sets the "failed" list (accessible through failed()) to a list of failed folder/file names and their reason for failure. If the root folder/file fails in some way (like if force is False and something goes wrong), an OSError will be raised instead.
    """
    # Check if src exists
    if not exists(src):
        raise FileNotFoundError("src file or folder could not be found")

    tdst = os.path.join(dst, Path(src).name) if into else dst

    if isdir(src):
        # If src is a directory
        # Ensure the output directory is available
        folder(tdst, force=force)

        # Merge into output directory
        merge(src, tdst, force=force)

        return tdst
    else:
        # If src is a file
        # Delete dst folder if it exists
        if isdir(tdst):
            rforce = qfile.default_force if force is None else force
            if rforce:
                shutil.rmtree(tdst)
            else:
                raise FileExistsError(
                    'cannot copy a file to where a folder is')

        # Make parent folder
        folder(parent(tdst), force=force)

        # Set failed state
        set_failed([])

        # Finally, copy file
        return shutil.copy(src, tdst)


def _move(src_path: Path, dst_path: Path):
    """Helper function to move."""
    if isdir(dst_path):
        raise FileExistsError("cannot move to directory")
    shutil.move(src_path, dst_path)


def move(src: PathLike, dst: PathLike, into: bool = False, force=None) -> str:
    """Moves a file or folder to the destination "dst". Returns the new path of the moved file or folder.

    This function is smart and lazy, so it will figure out the easiest way to move things around; for example, if it can get away with just renaming "src", it will do so.

    By default, "dst" is the path of the new file or folder, including the extension; if "into" is True, "dst" is treated as a folder (not a file name) to move the file or folder into. Parent folders will be created if they do not exist. If "dst" already exists, it will be overwritten or merged into. This function will throw an error if "src" is a folder parent of "dst".

    Sets the "failed" list (accessible through failed()) to a list of failed folder/file names and their reason for failure. If the root folder/file fails in some way (like if force is False and something goes wrong), an OSError will be raised instead.
    """
    if not exists(src):
        raise FileNotFoundError("src file or folder could not be found")

    # Just in case it's not done, set failed state to nothing
    set_failed([])

    src_path = Path(src).absolute()
    tdst = os.path.join(dst, src_path.name) if into else dst
    dst_path = Path(tdst).absolute()

    if dst_path.exists():
        if src_path.is_dir():
            # If src is a directory
            if dst_path.is_file():
                # Delete file if it exists and rename normally
                rforce = qfile.default_force if force is None else force
                if rforce:
                    os.remove(dst_path)
                    _move(src_path, dst_path)
                else:
                    raise FileExistsError(
                        "cannot move a folder to a file location")
            else:
                # Otherwise merge the folders together
                merge(src, tdst, move=True, force=force)
        else:
            # If src is a file
            if dst_path.is_dir():
                # Delete folder if it exists
                rforce = qfile.default_force if force is None else force
                if rforce:
                    shutil.rmtree(dst_path)
                else:
                    raise FileExistsError(
                        "cannot move a file to where a folder is")
            else:
                # Delete the file if it exists
                os.remove(dst_path)
            _move(src_path, dst_path)
    else:
        # Ensure the parent folder exists
        folder(parent(dst_path), force=force)
        _move(src_path, dst_path)

    return tdst
