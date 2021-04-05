"""Holds functions regarding file creation, writing, and reading."""

from . import PathLike, isdir, isfile, fsize, parent, check_force, check_size
from .dirs import folder

from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

import json
import pickle
import shutil


def touch(src: PathLike, clear: bool = False, force=None) -> bool:
    """Creates a file at "src". Parent folders will be created if they do not exist.

    Returns True if "src" was newly created or False if "src" already exists. If "clear" is True and the file already exists, it will be emptied.
    """
    if isfile(src):
        # If the file already exists, we just need to see if it needs to be cleared
        if clear:
            with open(src, "wb") as file:
                pass
        return False
    else:
        # Ensure parent directory exists
        folder(parent(src), force=force)

        # Delete folder if existing
        if check_force(force) and isdir(src):
            shutil.rmtree(src)

        # Create file
        with open(src, "x") as file:
            pass

        return True


# TODO: support links
# def link(src:str, dst:str, force=None) -> bool:
#     """Creates a symlink at "src" that points to "dst". Parent folders will be created if they do not exist.

#     Unlike os.symlink, if "dst" does not exist, this function will raise a FileNotFoundError. This function will also make sure the program has the ability to create symlinks.

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
#         if check_force(force): delete(src)
#         else: raise FileExistsError("cannot write symlink where file/folder already exists")
#     else:
#         # Ensure parent folder exists
#         folder(parent(src), force=force)

#     # Create symlink
#     os.symlink(dst, src)
#     return True

def write(src: PathLike, data='', mode: str = 'n', sep: str = ',', eol: str = "\n", code: str = "utf-8", key: Callable = None, force=None) -> int:
    """Writes the content (not necessarily a string) "data" to the file "src" with the given "mode", overwriting the entire file's contents. Returns the number of bytes written to the file.

    - If "mode" is 'n', "data" can be either a string, a bytes object, or an iterable of strings (interpreted as a list of lines) to write to a file. If given a non-string object, str() is called on that object and that is written instead.
    - If "mode" is 't', "data" is an iterable of an iterable of strings ([["a", "b"], ["c", "d"]]); the inner iterables are joined by "sep" and the outer iterable is then joined by "eol". By default you can use this to create a csv file. A basic attempt will be made to sanatize strings in "data" of the "sep" string.
    - If "mode" is 'j', "data" is a dictionary that will be written to the file in JSON format.
    - If "mode" is 'p', "data" is a python object that will be pickled (serialized) and afterwards written to the file.

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
        if check_force(force):
            shutil.rmtree(src_path)
        else:
            raise FileExistsError("cannot write data to an existing folder")

    # Make sure parent exists
    folder(parent(src_path), force=force)

    text = None
    raw = None

    if mode in {'n', 'b', 'l'}:
        # Normal mode
        if isinstance(data, str):
            text = data
        elif isinstance(data, bytes):
            raw = data
        elif isinstance(data, Iterable):
            text = eol.join(data)
        else:
            text = str(data)
    elif mode == 't':
        # Table mode
        text = eol.join([
            sep.join([str(i).replace(sep, "")
                     for i in line])  # Sanatize of sep
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
            return src_path.write_bytes(key(text.encode(code)))
        elif raw:
            return src_path.write_bytes(key(raw))
    else:
        if text:
            return src_path.write_text(text, code)
        elif raw:
            return src_path.write_bytes(raw)


def chunks(src: PathLike, size: int, even=False) -> Iterator[bytes]:
    """Reads the content from the file "src" in a generator format, yielding one chunk of bytes at a time. Each chunk returned is "size" bytes long. If the given file is empty, no chunks will be yielded by this function.

    The final chunk may be yielded with a size less than "size" bytes. Set "even" to True to raise a ValueError before reading "src" if the filesize in bytes is not a multiple of "size".
    """
    # Check if src size is valid
    if even and fsize(src) % size != 0:
        raise ValueError("src file contains an ending block of the wrong size")

    # Open file and yield chunks
    with open(src, "rb") as file:
        # I have restrained myself from using the walrus operator here, even though it fits perfectly
        chunk = file.read(size)
        while chunk:
            yield chunk
            chunk = file.read(size)


def lines(src: PathLike, empty=True, strip=False, code: str = "utf-8") -> Iterator[str]:
    """Reads the content from the file "src" in a generator format, yielding one line at a time. This is better than read(src, 'l') in many cases as it does not load every line into memory at once.

    If "empty" is set to False, this function will skip over empty lines in the file. If "strip" is set, spaces are stripped first.

    If "strip" is set to True, this function will strip each line before yielding it.

    "code" is the encoding to read from the file with; it defaults to "utf-8" but it can be set to "ascii".
    """
    # Get strip function to use
    if strip:
        sfunc = lambda x: x.strip()
    else:
        sfunc = lambda x: x.rstrip('\n')
    
    with open(src, "r", encoding=code) as file:
        if empty:
            for line in file:
                yield sfunc(line)
        else:
            for line in file:
                nline = sfunc(line)
                if nline:
                    yield nline


def read(src: PathLike, mode: str = 'n', sep: str = ',', code: str = "utf-8", err=True, key: Callable = None, errkey: Callable = None, force=None) -> Any:
    """Reads the content from the file "src" with the given "mode".

    By default, this function will raise a FileNotFoundError if "src" does not exist or a IsADirectoryError if "src" is a folder. If "err" is explicitly set to False (falsy values do not work), this function will return "None" in these cases instead.
    
    If "err" is set to anything else besides True or False, this function will attempt to write back to the "src" (using the write function) with "err" as the data to write in the given "mode" ('n', 'b', and 'l' all use 'n' write mode), returning the value of "err" or raising any errors along the way. Writing back to the file uses the "force" argument and the key "errkey". In modes 'j' and 'p', if any parsing errors occur and "err" is not True or False, this function will also make an attempt to overwrite "src".

    - If "mode" is 'n', this function will return a string with all the text in the file.
    - If "mode" is 'b', this function will return a bytes object of the content in the file, or whatever "key" returns based upon the bytes in that file.
    - If "mode" is 'l', this function will return a list of strings, with each string being one line in the file. It handles all three line endings ('\\r\\n', '\\r', and '\\n').
    - If "mode" is 't', this function will return a list of lists of strings. Each line in the file is read into a larger list as a string, and split by "sep". By default you can use this to read csv files. It handles all three line endings ('\\r\\n', '\\r', and '\\n')
    - If "mode" is 'j', this function will parse the content in the file as JSON and return a dictionary object with the file data.
    - If "mode" is 'p', this function will unpickle the content in the file (assumed to be a pickled python object) and return that object. BE VERY CAREFUL reading pickled files from untrusted sources, as it could lead to ACE (arbitrary code execution). JSON is a safer format that does not lead to ACE.

    "code" is the encoding to read from the file with; it defaults to "utf-8" when reading normal text (this is ignored in 'b' and 'p' mode) but it can be set to "ascii".

    "key", if provided, is a callable that takes binary data as an argument and converts it to output data to interpret in this function. You can use this to decrypt file data before it gets interpreted and returned. The binary data sent into the function is the raw binary data in the given file.
    """
    src_path = Path(src)
    # Check if file exists
    if not src_path.is_file():
        if err is True:
            if src_path.is_dir():
                raise IsADirectoryError("src is a folder and cannot be read")
            else:
                raise FileNotFoundError("src file not found")
        elif err is False:
            return None
        else:
            # Attempt to write back to file if it doesn't exist
            write(src, err, mode, sep, code=code, key=errkey, force=force)
            return err
    
    # Check if file is too large
    if check_size(src_path):
        raise ValueError("src file is too large to read")

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
        if type(err) is bool:
            return json.loads(data.decode(code))
        else:
            try:
                return json.loads(data.decode(code))
            except json.decoder.JSONDecodeError:
                # Failed decode means attempt to write back to file
                write(src, err, mode, sep, code=code, key=errkey, force=force)
                return err
    elif mode == 'p':
        # Pickle mode
        if type(err) is bool:
            return pickle.loads(data)
        else:
            try:
                return pickle.loads(data)
            except pickle.UnpicklingError:
                # Failed pickling error means attempt to write back to file
                write(src, err, mode, sep, code=code, key=errkey, force=force)
                return err
    else:
        raise ValueError(f'unknown mode "{mode}"')

# NOTE: there are no append() or insert() functions. These will not be supported as it's better to open a file object once and flush it constantly rather than open and close it over and over again.
