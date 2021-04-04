"""A python library for simplifying common file operations."""

__maintainer__  = "Zach K"
__version__     = "1.0.0"
__all__         = [
                    "default_force","failed","uuid","merge","clone","move","cut","copy","a_cut","a_copy",
                    "unmark", "paste","scan","glob","delete","wd","folder","touch","write","read",
                    "replace","rename","exists","isdir","isfile","islink","parent","rel","ftype",
                    "archive","extract"
                  ]


# TODO: Add some way of checking the progress of long file operations
# TODO: Support os.symlink without permission issues (currently os.symlink raises an OSError)
# TODO: Add methods of creating in-memory file-trees that can be modified by the same global methods


from contextlib import contextmanager
import sys
from typing import Any, Callable, Iterable, Iterator, Union
from pathlib import Path
from uuid import uuid4

import os
import shutil
import re
import json
import pickle
import threading

PathLike = Union[str, os.PathLike]

SameFileError = shutil.SameFileError



default_force:bool = False
"""Determines the default force mode for the methods in this library (You can specify the "force" parameter on supported function calls to overwrite this setting).

When a method's "force" mode is False, attempts to write/read to folders or make a folder where a file is already will raise an OSError of some kind. When "force" is True, these attempts will instead delete the folder/file and overwrite it with the proper file type. Note that sub-directories are automatically set to force mode.
"""

_thread_failed:dict[int, list[tuple[PathLike, bool, Exception]]] = {}
"""A dictionary of failed item lists mapped to thread identifiers. Use failed() to access."""

_cut_files:list[PathLike] = []
"""Files internally marked for being moved on call to paste()."""
_copied_files:list[PathLike] = []
"""Files internally marked for being copies on call to paste()."""

_repl_code = "utf-8"
"""Helper variable for the _repl_* helper methods"""



# This was really annoying to make but necessary
def _test():
    """Tests this library. If any error is raised then something is at fault."""
    # Temp folder
    name = uuid()
    with wd(name):
        # Test temp dir
        with wd("temp", temp=True): pass

        # Test write/read
        with wd("fs"):
            text = "rawtext"
            raw = b"stuff"
            lines = ["text", "textb", "textc"]
            table = [["a", "b", "c"], ["x", "y", "z"]]
            jdata = {"a": 1, "b": {"c": 2}}
            pdata = ["a", 1, _move]

            # Write
            write("empty.txt", "asdfasdf")
            write("empty.txt")
            write("text.txt", text)
            write("bytes.dat", raw)
            write("lines.txt", lines)
            write("table.csv", table, "t")
            write("data.json", jdata, "j")
            write("pickle.dat", pdata, "p")

            # Read
            assert read("empty.txt") == ""
            assert read("text.txt") == text
            assert read("bytes.dat", "b") == raw
            assert read("lines.txt", "l") == lines
            assert read("table.csv", "t") == table
            assert read("data.json", "j") == jdata
            assert read("pickle.dat", "p") == pdata

        # Create some starter things
        folder("a")
        write("c.txt", "text")
        touch("a/d.txt")
        touch("b/d.txt")
        touch("b/e.txt")
        touch("a/f/g.txt")

        # Ensure that clone works right
        clone("a", "x")
        assert exists("x/d.txt")
        assert exists("x/f/g.txt")
        # File into
        clone("c.txt", "x", into=True)
        assert read("x/c.txt") == "text"
        # Merging
        clone("x", "b")
        assert exists("b/f/g.txt")

        # Ensure that deletion works
        delete("x/c.txt", "x/f")
        assert exists("x")
        assert not exists("x/c.txt")
        assert not exists("x/f")

        # Ensure that move works right
        move("a", "h")
        assert exists("h/f/g.txt")
        assert not exists("a/f/g.txt")
        # Move into
        move("c.txt", "h", into=True)
        assert exists("h/c.txt")
        # Merging
        move("b", "h")
        assert not exists("b/e.txt")
        assert exists("h/e.txt")

        # Glob
        touch("p/x/y.txt")
        assert list(glob("p")) == [Path("p/x"), Path("p/x/y.txt")]
        assert list(glob("p", dirs=False)) == [Path("p/x/y.txt")]
        assert list(glob("p", files=False)) == [Path("p/x")]

        # Scan
        sdata = scan("p")
        assert len(sdata[0]) == 1
        assert len(sdata[1]) == 1
        # Scan with callable (only includes folders)
        sdata = scan("p", lambda name, folder: folder)
        assert len(sdata[0]) == 1
        assert len(sdata[1]) == 0

        # Cut-Copy-Paste
        cut("h", "p")
        unmark()
        cut("p/x/y.txt")
        a_copy("p")
        paste("q")
        assert exists("h")
        assert not exists("p/x/y.txt")
        assert exists("q/y.txt")
        assert exists("q/p")
        # Copy with root
        touch("p/x/y.txt")
        copy("p/x/y.txt")
        paste("q", "p")
        assert exists("q/x/y.txt")

        # Rename
        folder("i/l")
        rename("i/l", "k")
        assert exists("i/k")
        # Rename single regex
        write("i/x.txt", "text")
        rename("i/x.txt", r"\1.lol", r"(.*?)\.txt")
        assert exists("i/x.lol")
        # Rename multiple regex
        write("i/y.lol", "text")
        folder("i/l.lol")
        rename(glob("i"), r"\1.txt", r"(.*?)\.lol")
        assert exists("i/x.txt")
        assert exists("i/y.txt")
        assert exists("i/l.txt")

        # Replace
        write("n/a.txt", "lolasdflol")
        write("n/b.txt", "xasdfasdf")
        write("n/c.txt", b"\x00\x01\x02")
        write("m/a.txt", "lolasdflol")
        write("m/b.txt", "ioasdfio")
        write("m/c.txt", "lioasdflio")
        folder("m/n")
        # Replace single
        replace("n/a.txt", "asdf", "lol")
        assert read("n/a.txt") == "lollollol"
        # Replace regex
        replace("n/b.txt", re.compile(r"(x)asdf"), r"\1potato")
        assert read("n/b.txt") == "xpotatoasdf"
        # Replace bytes
        replace("n/c.txt", b"\x01", b"\x03")
        assert read("n/c.txt", 'b') == b"\x00\x03\x02"
        # Replace multiple (should include the folder m/n in the glob and throw no errors)
        replace(glob("m"), "asdf", "xd")
        assert read("m/a.txt") == "lolxdlol"
        assert read("m/b.txt") == "ioxdio"
        assert read("m/c.txt") == "lioxdlio"

        # Archive
        archive("i")
        assert exists("i.zip")

        # Extract
        extract("i.zip", "j")
        assert exists("j/x.txt")

        # Test force modes
        folder("h")
        write("o.txt", "text")
        global default_force
        df, default_force = default_force, False
        try:
            # Clone function
            try:
                clone("h", "o.txt")
                assert False, "cloned folder to file"
            except OSError: pass
            # Move function
            try:
                move("o.txt", "h")
                assert False, "moved file to folder"
            except OSError: pass
            # Folder function
            try:
                folder("o.txt")
                assert False, "made folder at file"
            except OSError: pass
            # Touch function
            try:
                touch("h")
                assert False, "made file at folder"
            except OSError: pass
            # Write function
            try:
                write("h", "lol")
                assert False, "wrote to folder"
            except OSError: pass
            # Read function
            try:
                read("h", err=True)
                assert False, "read from folder"
            except OSError: pass

            # Force mode on
            default_force = True
            
            folder("y")
            write("y", "text")
            assert isfile("y")
            clone("h", "y")
            assert isdir("y")
            write("y", "text")
            assert isfile("y")
            move("h", "y")
            assert isdir("y")
        finally:
            default_force = df

        # Print success message
        print("Tests succeeded")
    
    # input("Press enter to exit...")
    delete(name)



def _set_failed(failed_list:list):
    """Sets the failed list data for this thread to "failed_list"."""
    _thread_failed[threading.get_ident()] = failed_list

def failed(id:int=None) -> list[tuple[PathLike, bool, Exception]]:
    """Gets the list of failed items from the last function call in this thread, whether or not they are a folder, and the reason they failed. It is safe to work on this returned list and do other function calls because every function call in this library generates a new list.
    
    There are no guarantees that the first item in each tuple is definitely a string or a Path, only that it is one or the other.

    This method is thread safe and will only grab the latest failed information from the current thread. You can access other thread's failed lists by providing a "thread identifier" (returned by threading.get_ident(), for example).
    """
    sid = threading.get_ident() if id is None else id
    return _thread_failed[sid]

def uuid() -> str:
    """Generates a unique version 4 uuid as a string."""
    return str(uuid4())



def merge(src:PathLike, dst:PathLike, move=False, force=None) -> bool:
    """Copies "src" into "dst". All existing sub-folders in "src" will be copied too, and all existing files in "dst" will be overwritten (except folders where files should be and vice-versa). Files and folders in "dst" that don't exist in "src" are untouched. Unlike other functions which make the parent folders themselves, "src" and "dst" need to exist for this method to work.
    
    If "dst" is a parent of "src", "src" is moved out of "dst" first and afterwards merged into "dst". if "src" and "dst" are the same, this method does nothing to that folder. If "src" is a parent of "dst", this method will raise an error.

    Returns True on complete success, and False if any errors occurred.

    If "move" is True, files will be moved into the new directory instead of copied.

    NOTE: normally you will want to use clone() or move() instead of this method as they will create "dst" for you.

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
        # raise SameFileError("src and dst directories are the same")

    lfailed = []
    rforce = default_force if force is None else force

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
                        if not rforce: raise FileExistsError("cannot copy file where a directory is")
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

    _set_failed(lfailed)
    return not bool(lfailed)

def clone(src:PathLike, dst:PathLike, into:bool=False, force=None) -> str:
    """Clones a file or folder to the destination "dst". Returns the path of the file or folder clone.
    
    By default, "dst" is the path of the new file or folder, including the extension; if "into" is True, "dst" is treated as a folder (not a file name) to clone the file or folder into. Parent folders will be created if they do not exist. If "dst" already exists, it will be overwritten or merged into. This method will throw an error if "src" is a folder parent of "dst".

    Sets the "failed" list (accessible through failed()) to a list of failed folder/file names and their reason for failure. If the root folder/file fails in some way (like if force is False and something goes wrong), an OSError will be raised instead.
    """
    # Check if src exists
    if not exists(src): raise FileNotFoundError("src file or folder could not be found")

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
            rforce = default_force if force is None else force
            if rforce: shutil.rmtree(tdst)
            else: raise FileExistsError('cannot copy a file to where a folder is')
        
        # Make parent folder
        folder(parent(tdst), force=force)

        # Set failed state
        _set_failed([])

        # Finally, copy file
        return shutil.copy(src, tdst)

def _move(src_path:Path, dst_path:Path):
    """Helper function to move."""
    if isdir(dst_path): raise FileExistsError("cannot move to directory")
    shutil.move(src_path, dst_path)

def move(src:PathLike, dst:PathLike, into:bool=False, force=None) -> str:
    """Moves a file or folder to the destination "dst". Returns the new path of the moved file or folder.

    This method is smart and lazy, so it will figure out the easiest way to move things around; for example, if it can get away with just renaming "src", it will do so.
    
    By default, "dst" is the path of the new file or folder, including the extension; if "into" is True, "dst" is treated as a folder (not a file name) to move the file or folder into. Parent folders will be created if they do not exist. If "dst" already exists, it will be overwritten or merged into. This method will throw an error if "src" is a folder parent of "dst".

    Sets the "failed" list (accessible through failed()) to a list of failed folder/file names and their reason for failure. If the root folder/file fails in some way (like if force is False and something goes wrong), an OSError will be raised instead.
    """
    if not exists(src): raise FileNotFoundError("src file or folder could not be found")

    # Just in case it's not done, set failed state to nothing
    _set_failed([])

    src_path = Path(src).absolute()
    tdst = os.path.join(dst, src_path.name) if into else dst
    dst_path = Path(tdst).absolute()

    if dst_path.exists():
        if src_path.is_dir():
            # If src is a directory
            if dst_path.is_file():
                # Delete file if it exists and rename normally
                rforce = default_force if force is None else force
                if rforce:
                    os.remove(dst_path)
                    _move(src_path, dst_path)
                else:
                    raise FileExistsError("cannot move a folder to a file location")
            else:
                # Otherwise merge the folders together
                merge(src, tdst, move=True, force=force)
        else:
            # If src is a file
            if dst_path.is_dir():
                # Delete folder if it exists
                rforce = default_force if force is None else force
                if rforce: shutil.rmtree(dst_path)
                else: raise FileExistsError("cannot move a file to where a folder is")
            else:
                # Delete the file if it exists
                os.remove(dst_path)
            _move(src_path, dst_path)
    else:
        # Ensure the parent folder exists
        folder(parent(dst_path), force=force)
        _move(src_path, dst_path)
    
    return tdst



def cut(*src:Union[PathLike, Iterable[PathLike]]):
    """Marks a set of files and folders to be moved by paste(). Clears any marked files/folders."""
    unmark()
    a_cut(src)

def copy(*src:Union[PathLike, Iterable[PathLike]]):
    """Marks a set of files and folders to be copied by paste(). Clears any marked files/folders."""
    unmark()
    a_copy(src)

def a_cut(*src:Union[PathLike, Iterable[PathLike]]):
    """Works like cut() but doesn't unmark any already marked files/folders."""
    for item in src:
        if isinstance(item, (str, os.PathLike)) or not isinstance(item, Iterable):
            _cut_files.append(item)
        else:
            _cut_files.extend(item)

def a_copy(*src:Union[PathLike, Iterable[PathLike]]):
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

def paste(dst:PathLike, root:PathLike=None, force=None) -> bool:
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
                        helper(file, os.path.join(dst, rel_path.parent), into=True, force=force)
                    else:
                        # File is not in root
                        helper(file, dst, into=True, force=force)
                    lfailed.extend(failed())
                except OSError as e:
                    lfailed.append((file, isdir(), e))
    
    _set_failed(lfailed)
    unmark()



def _scan_r(src:PathLike, filter:Callable, sfolders:list[PathLike], sfiles:list[PathLike]):
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

# TODO: optimize/simplify this method (maybe a generator version?)
def scan(src:PathLike, filter:Callable=None, recurse:bool=True) -> tuple[list[str], list[str]]:
    """Scans the folder "src" and returns a tuple of: a list of the absolute paths of all subfolders, and a list of the absolute paths of all files/subfiles. The root folder is not included in the returned folder list.

    Consider using glob() if you want something simpler that yields values instead of generating a full list.

    "filter" is an optional callable that - provided an absolute path to a file/folder and a boolean saying whether or not the item is a folder - returns a boolean determining whether or not to scan/include that file/folder (True to include, False to ignore). Folders that get returned as False are not parsed through.

    By default, this will scan all subfolders too. Set "recurse" to False to disable this behavior.
    """
    if not isdir(src): raise NotADirectoryError("src is not a directory")

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

def glob(root:PathLike=".", ptrn:PathLike="**/*", dirs=True, files=True) -> Iterator[Path]:
    """A wrapper for Path(root).glob(str(ptrn)). Globs over all the folders and files in root.
    
    This method can automatically check the type of returned paths and filter out directories (folders) or files. Set dirs to False to filter out directories from the returned list, or set dirs to False to filter out files from the returned list. If you set both to False an error will be raised.
    """
    gen = Path(root).glob(str(ptrn))

    if dirs:
        if files:
            # Including both folders and files just means normally globing
            yield from gen
        else:
            # Filter out files but not folders
            for f in gen:
                if not f.is_file(): yield f
    else:
        if files:
            # Filter out folders but not files
            for f in gen:
                if not f.is_dir(): yield f
        else:
            # Can't filter out both files and folders.
            raise ValueError("cannot filter out both files and folders!")


def delete(*src:Union[PathLike, Iterable[PathLike]]) -> bool:
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
                if isdir(item): shutil.rmtree(item)
                # Normal files are deleted normally
                else: os.remove(item)
            except OSError as e:
                lfailed.append((item, isdir(item), e))
        else:
            # Item is a list
            for file in item:
                try:
                    # A directory is deleted recursively
                    if isdir(file): shutil.rmtree(file)
                    # Normal files are deleted normally
                    else: os.remove(file)
                except OSError as e:
                    lfailed.append((file, isdir(file), e))
    
    _set_failed(lfailed)
    return not bool(lfailed)

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
            except OSError: pass

def folder(src:PathLike, cwd:bool=False, force=None) -> bool:
    """Creates a folder at "src". Parent folders will be created if they do not exist.
    
    Setting "cwd" to True will result in changing the working directory to the given "src" folder (regardless of if it was just created or not)
    
    Returns True if "src" was newly created or False if "src" already exists.
    """
    if isdir(src):
        # If the folder already exists, we don't need to do anything
        # Except of course, enter it as a working directory if necessary
        if cwd: os.chdir(src)
        return False
    else:
        rforce = default_force if force is None else force
        if rforce:
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
        if cwd: os.chdir(src)
        return True

def touch(src:PathLike, clear:bool=False, force=None) -> bool:
    """Creates a file at "src". Parent folders will be created if they do not exist.
    
    Returns True if "src" was newly created or False if "src" already exists. If "clear" is True and the file already exists, it will be emptied.
    """
    if isfile(src):
        # If the file already exists, we just need to see if it needs to be cleared
        if clear:
            with open(src, "wb") as file: pass
        return False
    else:
        # Ensure parent directory exists
        folder(parent(src), force=force)

        # Delete folder if existing
        rforce = default_force if force is None else force
        if rforce and isdir(src):
            shutil.rmtree(src)
        
        # Create file
        with open(src, "x") as file: pass

        return True

# TODO: support links
# def link(src:str, dst:str, force=None) -> bool:
#     """Creates a symlink at "src" that points to "dst". Parent folders will be created if they do not exist.

#     Unlike os.symlink, if "dst" does not exist, this function will raise a FileNotFoundError. This method will also make sure the program has the ability to create symlinks.

#     Returns True if "src" was newly created or False if "src" already exists as a symlink to the same "dst".
#     """
#     # Check if dst exists
#     if not exists(dst): raise FileNotFoundError("dst of symlink does not exist")
    
#     if islink(src):
#         if os.readlink(src) == dst:
#             return False
#         else:
#             os.remove(src)
#     elif exists(src):
#         rforce = default_force if force is None else force
#         if rforce: delete(src)
#         else: raise FileExistsError("cannot write symlink where file/folder already exists")
#     else:
#         # Ensure parent folder exists
#         folder(parent(src), force=force)

#     # Create symlink
#     os.symlink(dst, src)
#     return True



def write(src:PathLike, data='', mode:str='n', sep:str=',', eol:str="\n", code:str="utf-8", key:Callable=None, force=None):
    """Writes the content "data" to the file "src" with the given "mode", overwriting the entire file's contents.

    If "mode" is 'n', "data" can be either a string, a bytes object, or an iterable of strings (interpreted as a list of lines) to write to a file. If given a non-string object, str() is called on that object and that is written instead.

    If "mode" is 't', "data" is an iterable of an iterable of strings ([["a", "b"], ["c", "d"]]); the inner iterables are joined by "sep" and the outer iterable is then joined by "eol". By default you can use this to create a csv file. A basic attempt will be made to sanatize strings in "data" of the "sep" string.

    If "mode" is 'j', "data" is a dictionary that will be written to the file in JSON format.

    If "mode" is 'p', "data" is a python object that will be pickled (serialized) and afterwards written to the file.

    "eol" is the end of line character used to join lines together.
    "code" is the encoding to write to the file with; it defaults to "utf-8" when the text is not a bytestring but can be set to "ascii".

    "key", if provided, is a callable that takes binary data as an argument and converts it to output binary data to write to the file. You can use this to encrypt data before it gets sent to a file. The binary data sent into the function is either a string that would have been written to the file encoded with "code", or raw binary data.
    """
    # If no data, then run touch clear instead
    if not data and mode != "j" and mode != "p":
        touch(src, clear=True)
        return
    
    src_path = Path(src)

    # Ensure the location is not a folder
    if src_path.is_dir():
        rforce = default_force if force is None else force
        if rforce: shutil.rmtree(src_path)
        else: raise FileExistsError("cannot write data to an existing folder")
    
    # Make sure parent exists
    folder(parent(src_path), force=force)

    text = None
    raw = None

    if mode == 'n':
        # Normal mode
        if   isinstance(data, str):         text = data
        elif isinstance(data, bytes):       raw  = data
        elif isinstance(data, Iterable):    text = eol.join(data)
        else:                               text = str(data)
    elif mode == 't':
        # Table mode
        text = eol.join([
            sep.join([str(i).replace(sep, "") for i in line]) # Sanatize of sep
            for line in data
        ])
    elif mode == 'j':
        # JSON mode
        text = json.dumps(data)
    elif mode == 'p':
        # Pickle mode
        raw = pickle.dumps(data)
    else:
        raise ValueError(f'unknown mode "{mode}"')
    
    if isinstance(key, Callable):
        if text:
            src_path.write_bytes(key(text.encode(code)))
        elif raw:
            src_path.write_bytes(key(raw))
    else:
        if text:
            src_path.write_text(text, code)
        elif raw:
            src_path.write_bytes(raw)

def read(src:PathLike, mode:str='n', sep:str=',', code:str="utf-8", err:bool=False, key:Callable=None) -> Any:
    """Reads the content from the file "src" with the given "mode".

    By default, this method will not raise a FileNotFoundError or an error if "src" is a directory, but will instead return None. Set "err" to True to raise FileNotFoundError instead.

    If "mode" is 'n', this method will return a string with all the text in the file.

    If "mode" is 'b', this method will return a bytes object of the content in the file, or whatever "key" returns based upon the bytes in that file.

    If "mode" is 'l', this method will return a list of strings, with each string being one line in the file. It handles all three line endings ('\\r\\n', '\\r', and '\\n').

    If "mode" is 't', this method will return a list of lists of strings. Each line in the file is read into a larger list as a string, and split by "sep". By default you can use this to read csv files. It handles all three line endings ('\\r\\n', '\\r', and '\\n')

    If "mode" is 'j', this method will parse the content in the file as JSON and return a dictionary object with the file data.
    
    If "mode" is 'p', this method will unpickle the content in the file (assumed to be a pickled python object) and return that object. BE VERY CAREFUL reading pickled files from untrusted sources, as it could lead to ACE (arbitrary code execution). JSON is a safer format that does not lead to ACE.

    "code" is the encoding to read from the file with; it defaults to "utf-8" when reading normal text (this is ignored in 'b' and 'p' mode) but it can be set to "ascii".
    
    "key", if provided, is a callable that takes binary data as an argument and converts it to output data to interpret in this function. You can use this to decrypt file data before it gets interpreted and returned. The binary data sent into the function is the raw binary data in the given file.
    """
    src_path = Path(src)
    # Check if file exists
    if not src_path.is_file():
        if err:
            raise FileNotFoundError("src file either not found or is a folder")
        else:
            return None

    # Read bytes from file
    data = src_path.read_bytes()
    # Convert data if necessary
    if isinstance(key, Callable):
        data = key(data)
    
    # Do things based on mode
    if mode == 'n':
        # Normal mode
        return data.decode(code)
    elif mode == 'b':
        # Bytes mode
        return data
    elif mode == 'l':
        # Lines mode
        return data.decode(code).splitlines()
    elif mode == 't':
        # Table mode
        return [line.split(sep) for line in data.decode(code).splitlines()]
    elif mode == 'j':
        # JSON mode
        return json.loads(data.decode(code))
    elif mode == 'p':
        # Pickle mode
        return pickle.loads(data)
    else:
        raise ValueError(f'unknown mode "{mode}"')

# NOTE: there are no append() or insert() methods. These will not be supported as it's better to open a file object once and flush it constantly rather than open and close it over and over again.

def _repl_bytes(src:PathLike, old:bytes, new:bytes):
    """Helper method to replace() that replaces bytes in a file"""
    with open(src, "rb") as file:
        data = file.read().replace(old, new)
    with open(src, "wb") as file:
        file.write(data)

def _repl_str(src:PathLike, old:str, new:str):
    """Helper method to replace() that replaces strings in a file"""
    with open(src, "r", encoding=_repl_code) as file:
        data = file.read().replace(old, new)
    with open(src, "w", encoding=_repl_code) as file:
        file.write(data)

def _repl_pattern(src:PathLike, old:re.Pattern, new:str):
    """Helper method to replace() that replaces patterns in a file"""
    with open(src, "r", encoding=_repl_code) as file:
        data = old.sub(new, file.read())
    with open(src, "w", encoding=_repl_code) as file:
        file.write(data)

def replace(src:Union[PathLike, Iterable[PathLike]], old:Union[str, bytes, re.Pattern], new:Union[str, bytes], code:str="utf-8") -> bool:
    """Replaces all instances of "old" with "new" in the "src" file(s).
    
    Returns True on complete success and False if there were any errors. If only one file is given, the error would be raised.
    
    "old" can be a string, a bytes object, or a compiled re.Pattern object.
    If a string or bytes, it is treated literally as exact data to replace.
    If it is a regex object, it will search for that regex in files (in text mode) and replace any matches with the "new" string (which may have indicators like r'\\1', and r'\\2' to denote capture groups). This uses the "Pattern.sub()" function in base python.

    If multiple files are provided in "src", the "failed" list (accessible through failed()) is set to a list of files that could not have their contents replaced.
    """
    global _repl_code
    _repl_code = code

    # Get helper method
    if isinstance(old, bytes):
        # Replace bytes
        if not isinstance(new, bytes): raise ValueError("new must be a bytes object if old is a bytes object")
        helper = _repl_bytes
    elif isinstance(old, str):
        # Replace string
        if not isinstance(new, str): raise ValueError("new must be a string if old is a string")
        helper = _repl_str
    elif isinstance(old, re.Pattern):
        # Replace pattern
        if not isinstance(new, str): raise ValueError("new must be a string if old is a Pattern")
        helper = _repl_pattern
    else:
        raise ValueError("Arguments provided are incorrect")
    
    # Call helper method on files
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
    
        _set_failed(lfailed)
        return not bool(lfailed)



# TODO: figure out a better way to rename than os.rename() (which uh, might be hard)
def rename(src:Union[PathLike, Iterable[PathLike]], name:str, regex:Union[str, re.Pattern]=None) -> Union[str, list[str]]:
    """Gives the "src" file/folder(s) the new "name" (including the extension if it is a file). Note that renaming something to a file or folder that already exists will cause an error. Returns a string or list of strings to the paths of the new file names.

    Unlike the os.rename() function, "name" is an exact name and does not include the file path.
    
    If "regex" is given, it specifies a regex that must matched with in the file name (not including the file path) to replace with "name". "name" will be used as the replacement in the "Pattern.sub" method.

    If multiple files are provided in "src", the "failed" list (accessible through failed()) is set to a list of files and folders that failed to be renamed.
    """
    # Check if name contains invalid characters
    if "/" in name or r"\\" in name: raise OSError("replacement name cannot contain any folder separators")

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
                        new_name = file_path.parent.joinpath(match.expand(name))
                        os.rename(file_path, new_name)
                        new_names.append(str(new_name))
                    else:
                        new_names.append(file)
                except OSError as e:
                    lfailed.append((file, isdir(file), e))
                    new_names.append(file)
            
            _set_failed(lfailed)
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
            
            _set_failed(lfailed)
            return new_names

exists = os.path.exists
"""This is a direct reference to os.path.exists."""
isdir = os.path.isdir
"""This is a direct reference to os.path.isdir."""
isfile = os.path.isfile
"""This is a direct reference to os.path.isfile."""
islink = os.path.islink
"""This is a direct reference to os.path.islink."""

def parent(child:PathLike) -> Path:
    """Returns the parent of this child element."""
    return Path(child).absolute().parent

def rel(child:PathLike, parent:PathLike) -> Union[Path, None]:
    """Returns the relative path of child in parent as given by Path.relative_to(), or None if "child" is not a child of "parent". Relative paths will be turned into absolute paths.
    
    For example, If child is "myfolder/thing/that" and parent is "myfolder", this will return Path("thing/that")."""
    try:
        return Path(os.path.abspath(child)).relative_to(os.path.abspath(parent))
    except ValueError:
        return None

def ftype(src:PathLike) -> tuple[Union[None, str], bool]:
    """Returns a string representing the type of the file/folder at "src" and whether or not "src" is a link. The string is either 'file' or 'dir', or None if it does not exist."""
    link = islink(src)
    if isdir(src):
        return 'dir', link
    elif isfile(src):
        return 'file', link
    else:
        return None, link



def archive(src:PathLike, dst:PathLike='.', format:str='zip', into:bool=True, temp=False, force=None) -> str:
    """Archives all of the content in folder "src" into an archive and then moves the archive into "dst". Returns the path of the created archive. Note that empty folders will not be included in the archive.

    By default, "dst" is treated as a folder (not a file name) to put the archive into. Parent folders will be created if they do not exist; if "into" is False, "dst" is the path and name of the new archive including the extension (which does not have to match the archive format). If "dst" already exists, it will be overwritten or merged into.

    On import, this module will attempt to register the formats '7zip' (if the py7zr module is installed) and 'jar' (which is just a renamed zip file).

    If "temp" is True, this method will also delete the "src" folder.

    Default supported types are those supported by shutil.make_archive() (so custom formats registered through shutil.register_archive_format() work too). Note that the type does not have to match the file extension of "dst" if into is False.
    """
    # Check if src and dst are valid
    if not isdir(src): NotADirectoryError("src is not a directory")
    rforce = default_force if force is None else force
    if not rforce:
        tdst = os.path.join(dst, Path(src).name) if into else dst
        if isfile(tdst): FileExistsError("cannot create an archive where a folder exists!")
    
    src_path = Path(src).absolute()
    with wd(src_path.parent):
        # Generate unique temporary folder name
        name = uuid()
        # Create the archive
        file = shutil.make_archive(os.path.join(name, src_path.stem), format, src_path.name)
    # Move to proper location
    out = move(file, dst, into=into, force=True)
    # Delete empty directory
    # If it's not empty, we have bigger problems to worry about
    os.rmdir(name)

    # Delete src folder if move is true
    if temp: shutil.rmtree(src)

    # Return archive name
    return out

def extract(src:PathLike, dst:PathLike='.', temp=False, force=None) -> bool:
    """Extracts the content in the archive "src" and merges it with "dst". Merges folders and overwrites files that are already in "dst". The type of the archive is assumed. The "dst" folder will be created if it does not exist. See archive() for extra added filetypes. Returns True on complete success, False on failure.

    If "temp" is True, this method will also delete the "src" archive.

    Supported file types are those supported by shutil.unpack_archive().

    Sets "failed" to a list of failed items that could not be extracted. Note that these failed paths will have a random uuid in them.
    """
    # Check if src and dst are valid
    if not isfile(src): FileNotFoundError("src is not a file")
    rforce = default_force if force is None else force
    if not rforce and isfile(dst): FileExistsError("cannot extract an archive to a file")

    # Generate unique temporary folder name
    name = uuid()
    os.mkdir(name)
    try:
        # Unpack archive into temporary folder
        shutil.unpack_archive(src, name)
        # Merge into dst
        success = move(name, dst, force=force)

        if temp: os.remove(src)
    except OSError as e:
        # Panic delete the temp folder
        shutil.rmtree(name)
        # Reraise exception
        raise e.with_traceback(sys.exc_info()[2])
    
    return success

# Attempt to register file formats
# .7z
try:
    import py7zr

    shutil.register_archive_format('7zip', py7zr.pack_7zarchive, description='7zip archive')
    shutil.register_unpack_format('7zip', ['.7z'], py7zr.unpack_7zarchive)
except ModuleNotFoundError:
    pass

# .jar
def _pack_jar(base_name, base_dir, verbose=0, dry_run=0, logger=None, owner=None, group=None):
    # HACK: call zipfile without the owner and group vars
    return shutil._make_zipfile(base_name, base_dir, verbose, dry_run, logger)
def _unpack_jar(filename, extract_dir):
    # HACK: Have to rename the jar file to zip to get it to realize it's just a zip file
    fpath = Path(filename)
    nname = fpath.parent.joinpath(fpath.stem + ".zip")
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



if __name__ == "__main__":
    _test()