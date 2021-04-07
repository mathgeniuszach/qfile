"""Sub-module for archiving functions."""

from . import PathLike, isdir, isfile, check_force
from .relocate import move

from pathlib import Path
from tempfile import TemporaryDirectory

import shutil
import os


def archive(src: PathLike, dst: PathLike = '.', format: str = 'zip', into: bool = True, temp=False, force=None) -> str:
    """Archives all of the content in folder "src" into an archive and then moves the archive into "dst". Returns the path of the created archive. Note that empty folders will not be included in the archive.

    By default, "dst" is treated as a folder (not a file name) to put the archive into. Parent folders will be created if they do not exist; if "into" is False, "dst" is the path and name of the new archive including the extension (which does not have to match the archive format). If "dst" already exists, it will be overwritten or merged into.

    On import, this module will attempt to register the formats '7zip' (if the py7zr module is installed) and 'jar' (which is just a renamed zip file).

    If "temp" is True, this function will also delete the "src" folder.

    Default supported types are those supported by shutil.make_archive() (so custom formats registered through shutil.register_archive_format() work too). Note that the type does not have to match the file extension of "dst" if into is False.
    """
    # Check if src and dst are valid
    if not isdir(src):
        NotADirectoryError("src is not a directory")
    if not check_force(force):
        tdst = os.path.join(dst, Path(src).name) if into else dst
        if isfile(tdst):
            FileExistsError("cannot create an archive where a folder exists!")

    src_path = Path(src).absolute()
    tdir = TemporaryDirectory()
    try:
        file = shutil.make_archive(
            os.path.join(tdir.name, src_path.stem), format, src_path
        )
        # Move to proper location
        out = move(file, dst, into=into, force=True)
    finally:
        tdir.cleanup()

    # Delete src folder if move is true
    if temp:
        shutil.rmtree(src)

    # Return archive name
    return out


def extract(src: PathLike, dst: PathLike = '.', temp=False, force=None) -> bool:
    """Extracts the content in the archive "src" and merges it with "dst". Merges folders and overwrites files that are already in "dst". The type of the archive is assumed. The "dst" folder will be created if it does not exist. See archive() for extra added filetypes. Returns True on complete success, False on failure.

    If "temp" is True, this function will also delete the "src" archive.

    Supported file types are those supported by shutil.unpack_archive().

    Sets "failed" to a list of failed items that could not be extracted. Note that these failed paths will have a random uuid in them.
    """
    # Check if src and dst are valid
    if not os.path.isfile(src):
        FileNotFoundError("src is not a file")
    if not check_force(force) and os.path.isfile(dst):
        FileExistsError("cannot extract an archive to a file")

    # Generate unique temporary folder name
    tdir = TemporaryDirectory()
    try:
        # Unpack archive into temporary folder
        shutil.unpack_archive(src, tdir.name)
        # Merge into dst
        success = move(tdir.name, dst, force=force)
        # Delete src folder if tmp
        if temp:
            os.remove(src)
    finally:
        tdir.cleanup()

    return success


# Attempt to register file formats
# .7z
try:
    import py7zr

    shutil.register_archive_format(
        '7zip', py7zr.pack_7zarchive, description='7zip archive')
    shutil.register_unpack_format('7zip', ['.7z'], py7zr.unpack_7zarchive)
except ModuleNotFoundError:
    pass

# .jar


def _pack_jar(base_name, base_dir, verbose=0, dry_run=0, logger=None, owner=None, group=None):
    # HACK: call zipfile without the owner and group vars
    name = shutil._make_zipfile(base_name, base_dir, verbose, dry_run, logger)
    # Rename to jar file
    nname = Path(name).with_suffix(".jar")
    os.rename(name, nname)
    return str(nname)


def _unpack_jar(filename, extract_dir):
    # HACK: Have to rename the jar file to zip to get it to realize it's just a zip file
    nname = Path(filename).with_suffix(".zip")
    os.rename(filename, nname)
    try:
        # Normal zip thing (Had to go into shutil.py to get it)
        shutil._unpack_zipfile(nname, extract_dir)
    finally:
        # Rename back to jar
        os.rename(nname, filename)


shutil.register_archive_format('jar', _pack_jar, description='Java jar file')
shutil.register_unpack_format('jar', ['.jar'], _unpack_jar)

# TODO: support .iso files through pycdlib
# TODO: support .rar files through the command line
# TODO: support other arbitrary file types
