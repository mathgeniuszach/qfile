# API
This is the entire api for qfile. It matches with version 1.1.0.

- [Renamed Standard Functions](#renamed-standard-functions)
- [Generic Operations](#generic-operations)
- [Folder Operations](#folder-operations)
- [File Operations](#file-operations)
- [Relocating Operations](#relocating-operations)
- [Replace Operations](#replace-operations)
- [Clipboard-Like Operations](#clipboard-like-operations)
- [Archiving Operations](#archiving-operations)

## Renamed Standard Functions
These are simply renamed versions of standard functions for easy access:

| Function     | Standard Function |
| ------------ | ----------------- |
| qfile.exists | os.path.exists    |
| qfile.isdir  | os.path.isdir     |
| qfile.isfile | os.path.isfile    |
| qfile.islink | os.path.islink    |
| qfile.fsize  | os.path.getsize   |
| qfile.join   | os.path.join      |


## Globals
These are settings for the entire library.

### default_force
**default_force: bool = False**

Determines the default force mode for the functions in this library (You can specify the "force" parameter on supported function calls to overwrite this setting).

When a function's "force" mode is False, attempts to write/read to folders or make a folder where a file is already will raise an OSError of some kind. When "force" is True, these attempts will instead delete the folder/file and overwrite it with the proper file type. Note that sub-directories are automatically set to force mode.

### max_read_size
**max_read_size: int = -1**

Determines the maximum file size in bytes the read() function can handle. Attempting to read from a file larger than this number will cause the read function to raise a ValueError. Set to -1 (default) for no limit.

## Generic Operations

### parent
**parent(child: Union[str, os.PathLike]) -> pathlib.Path**

Returns the parent of this child element.

### delete
**delete(\*src: Union[str, os.PathLike, Iterable[Union[str, os.PathLike]]]) -> bool**

Deletes the file(s) or folder(s) at "src". Deletes all sub-folders and files. Returns True if completely successful, and False otherwise.

If a single string is given, returns True if the "src" was deleted or False if "src" does not exist. If a list of strings is given, returns a list of booleans of whether or not the "src" file existed. This function calls itself recusively, so lists of lists of strings are possible too.

The "failed" list (accessible through failed()) is always set to a list of files and folders that failed, so this function will never raise an OSError.

### force
**force(force: bool = True)**

A context manager for temporarily setting the default_force mode. e.g. "with force():" would make all included operations within the "with" block operate under force=True. This will reset "default_force" when the with block finishes.

### uuid
**uuid() -> str**

Generates a unique version 4 uuid as a string.

### ftype
**ftype(src: Union[str, os.PathLike]) -> tuple**

Returns a string representing the type of the file/folder at "src" and whether or not "src" is a link. The string is either 'file' or 'dir', or None if it does not exist.

### rel
**rel(child: Union[str, os.PathLike], parent: Union[str, os.PathLike]) -> Optional[pathlib.Path]**

Returns the relative path of child in parent as given by Path.relative_to(), or None if "child" is not a child of "parent". Relative paths will be turned into absolute paths.

For example, If child is "myfolder/thing/that" and parent is "myfolder", this will return Path("thing/that").

### failed
**failed(id: int = None) -> list**

Gets the list of failed items from the last function call in this thread, whether or not they are a folder, and the reason they failed. It is safe to work on this returned list and do other function calls because every function call in this library generates a new list.

There are no guarantees that the first item in each tuple is definitely a string or a Path, only that it is one or the other.

This function is thread safe and will only grab the latest failed information from the current thread. You can access other thread's failed lists by providing a "thread identifier" (returned by threading.get_ident(), for example).



## Folder Operations

### scan
**scan(src: Union[str, os.PathLike], filter: Callable = None, recurse: bool = True) -> tuple**

Scans the folder "src" and returns a tuple of: a list of the absolute paths of all subfolders, and a list of the absolute paths of all files/subfiles. The root folder is not included in the returned folder list.

Consider using glob() if you want something simpler that yields values instead of generating a full list.

"filter" is an optional callable that - provided an absolute path to a file/folder and a boolean saying whether or not the item is a folder - returns a boolean determining whether or not to scan/include that file/folder (True to include, False to ignore). Folders that get returned as False are not parsed through.

By default, this will scan all subfolders too. Set "recurse" to False to disable this behavior.

### glob
**glob(root: Union[str, os.PathLike] = '.', ptrn: Union[str, os.PathLike] = '\*\*/\*', dirs=True, files=True) -> Iterator[pathlib.Path]**

A wrapper for Path(root).glob(str(ptrn)). Globs over all the folders and files in root.

This function can automatically check the type of returned paths and filter out directories (folders) or files. Set dirs to False to filter out directories from the returned list, or set dirs to False to filter out files from the returned list. If you set both to False an error will be raised.

### wd
**wd(wd, force=None, temp=False)**

A context manager for temporarily entering a working directory with a with statement. Just use "with wd('working_directory'):". If the working directory does not exist, it will be created automatically. If "temp" is True, the working directory will also be deleted when exiting the "with" block. Failing to delete the temporary directory will not result in an error.

### folder
**folder(src: Union[str, os.PathLike], cwd: bool = False, force=None) -> bool**

Creates a folder at "src". Parent folders will be created if they do not exist.

Setting "cwd" to True will result in changing the working directory to the given "src" folder (regardless of if it was just created or not)

Returns True if "src" was newly created or False if "src" already exists.



## File Operations

### touch
**touch(src: Union[str, os.PathLike], clear: bool = False, force=None) -> bool**

Creates a file at "src". Parent folders will be created if they do not exist.

Returns True if "src" was newly created or False if "src" already exists. If "clear" is True and the file already exists, it will be emptied.

### write
**write(src: Union[str, os.PathLike], data='', mode: str = 'n', sep: str = ',', eol: str = '\n', code: str = 'utf-8', key: Callable = None, force=None) -> int**

Writes the content (not necessarily a string) "data" to the file "src" with the given "mode", overwriting the entire file's contents. Returns the number of bytes written to the file.

- If "mode" is 'n', "data" can be either a string, a bytes object, or an iterable of strings (interpreted as a list of lines) to write to a file. If given a non-string object, str() is called on that object and that is written instead.
- If "mode" is 't', "data" is an iterable of an iterable of strings ([["a", "b"], ["c", "d"]]); the inner iterables are joined by "sep" and the outer iterable is then joined by "eol". By default you can use this to create a csv file. A basic attempt will be made to sanatize strings in "data" of the "sep" string.
- If "mode" is 'j', "data" is a dictionary that will be written to the file in JSON format.
- If "mode" is 'p', "data" is a python object that will be pickled (serialized) and afterwards written to the file.

"eol" is the end of line character used to join lines together.

"code" is the encoding to write to the file with; it defaults to "utf-8" when the text is not a bytestring but can be set to "ascii".

"key", if provided, is a callable that takes binary data as an argument and converts it to output binary data to write to the file. You can use this to encrypt data before it gets sent to a file. The binary data sent into the function is either a string that would have been written to the file encoded with "code", or raw binary data.

### chunks
**chunks(src: Union[str, os.PathLike], size: int, even=False) -> Iterator[bytes]**

Reads the content from the file "src" in a generator format, yielding one chunk of bytes at a time. Each chunk returned is "size" bytes long. If the given file is empty, no chunks will be yielded by this function.

The final chunk may be yielded with a size less than "size" bytes. Set "even" to True to raise a ValueError before reading "src" if the filesize in bytes is not a multiple of "size".

### lines
**lines(src: Union[str, os.PathLike], empty=True, strip=False, code: str = 'utf-8') -> Iterator[str]**

Reads the content from the file "src" in a generator format, yielding one line at a time. This is better than read(src, 'l') in many cases as it does not load every line into memory at once.

If "empty" is set to False, this function will skip over empty lines in the file. If "strip" is set, spaces are stripped first.

If "strip" is set to True, this function will strip each line before yielding it.

"code" is the encoding to read from the file with; it defaults to "utf-8" but it can be set to "ascii".

### read
**read(src: Union[str, os.PathLike], mode: str = 'n', sep: str = ',', code: str = 'utf-8', err=True, key: Callable = None, errkey: Callable = None, force=None) -> Any**

Reads the content from the file "src" with the given "mode".

By default, this function will raise a FileNotFoundError if "src" does not exist or a IsADirectoryError if "src" is a folder. If "err" is explicitly set to False (falsy values do not work), this function will return "None" in these cases instead.

If "err" is set to anything else besides True or False, this function will attempt to write back to the "src" (using the write function) with "err" as the data to write in the given "mode" ('n', 'b', and 'l' all use 'n' write mode), returning the value of "err" or raising any errors along the way. Writing back to the file uses the "force" argument and the key "errkey". In modes 'j' and 'p', if any parsing errors occur and "err" is not True or False, this function will also make an attempt to overwrite "src".

- If "mode" is 'n', this function will return a string with all the text in the file.
- If "mode" is 'b', this function will return a bytes object of the content in the file, or whatever "key" returns based upon the bytes in that file.
- If "mode" is 'l', this function will return a list of strings, with each string being one line in the file. It handles all three line endings ('\r\n', '\r', and '\n').
- If "mode" is 't', this function will return a list of lists of strings. Each line in the file is read into a larger list as a string, and split by "sep". By default you can use this to read csv files. It handles all three line endings ('\r\n', '\r', and '\n')
- If "mode" is 'j', this function will parse the content in the file as JSON and return a dictionary object with the file data.
- If "mode" is 'p', this function will unpickle the content in the file (assumed to be a pickled python object) and return that object. BE VERY CAREFUL reading pickled files from untrusted sources, as it could lead to ACE (arbitrary code execution). JSON is a safer format that does not lead to ACE.

"code" is the encoding to read from the file with; it defaults to "utf-8" when reading normal text (this is ignored in 'b' and 'p' mode) but it can be set to "ascii".

"key", if provided, is a callable that takes binary data as an argument and converts it to output data to interpret in this function. You can use this to decrypt file data before it gets interpreted and returned. The binary data sent into the function is the raw binary data in the given file.



## Relocating Operations

### merge
**merge(src: Union[str, os.PathLike], dst: Union[str, os.PathLike], move=False, force=None) -> bool**

Copies "src" into "dst". All existing sub-folders in "src" will be copied too, and all existing files in "dst" will be overwritten (except folders where files should be and vice-versa). Files and folders in "dst" that don't exist in "src" are untouched. Unlike other functions which make the parent folders themselves, "src" and "dst" need to exist for this function to work.

If "dst" is a parent of "src", "src" is moved out of "dst" first and afterwards merged into "dst". if "src" and "dst" are the same, this function does nothing to that folder. If "src" is a parent of "dst", this function will raise an error.

Returns True on complete success, and False if any errors occurred.

If "move" is True, files will be moved into the new directory instead of copied.

NOTE: normally you will want to use clone() or move() instead of this function as they will create "dst" for you.

Sets the "failed" list (accessible through failed()) to a list of failed folder/file names and their reason for failure.

### clone
**clone(src: Union[str, os.PathLike], dst: Union[str, os.PathLike], into: bool = False, force=None) -> str**

Clones a file or folder to the destination "dst". Returns the path of the file or folder clone.

By default, "dst" is the path of the new file or folder, including the extension; if "into" is True, "dst" is treated as a folder (not a file name) to clone the file or folder into. Parent folders will be created if they do not exist. If "dst" already exists, it will be overwritten or merged into. This function will throw an error if "src" is a folder parent of "dst".

Sets the "failed" list (accessible through failed()) to a list of failed folder/file names and their reason for failure. If the root folder/file fails in some way (like if force is False and something goes wrong), an OSError will be raised instead.

### move
**move(src: Union[str, os.PathLike], dst: Union[str, os.PathLike], into: bool = False, force=None) -> str**

Moves a file or folder to the destination "dst". Returns the new path of the moved file or folder.

This function is smart and lazy, so it will figure out the easiest way to move things around; for example, if it can get away with just renaming "src", it will do so.

By default, "dst" is the path of the new file or folder, including the extension; if "into" is True, "dst" is treated as a folder (not a file name) to move the file or folder into. Parent folders will be created if they do not exist. If "dst" already exists, it will be overwritten or merged into. This function will throw an error if "src" is a folder parent of "dst".

Sets the "failed" list (accessible through failed()) to a list of failed folder/file names and their reason for failure. If the root folder/file fails in some way (like if force is False and something goes wrong), an OSError will be raised instead.



## Replace Operations

### replace
**replace(src: Union[str, os.PathLike, Iterable[Union[str, os.PathLike]]], old: Union[str, bytes, re.Pattern], new: Union[str, bytes], code: str = 'utf-8') -> bool**

Replaces all instances of "old" with "new" in the "src" file(s).

Returns True on complete success and False if there were any errors. If only one file is given, the error would be raised.

"old" can be a string, a bytes object, or a compiled re.Pattern object.
If a string or bytes, it is treated literally as exact data to replace.
If it is a regex object, it will search for that regex in files (in text mode) and replace any matches with the "new" string (which may have indicators like r'\1', and r'\2' to denote capture groups). This uses the "Pattern.sub()" function in base python.

If multiple files are provided in "src", the "failed" list (accessible through failed()) is set to a list of files that could not have their contents replaced.

### rename
**rename(src: Union[str, os.PathLike, Iterable[Union[str, os.PathLike]]], name: str, regex: Union[str, re.Pattern] = None) -> Union[str, list[str]]**

Gives the "src" file/folder(s) the new "name" (including the extension if it is a file). Note that renaming something to a file or folder that already exists will cause an error. Returns a string or list of strings to the paths of the new file names.

Unlike the os.rename() function, "name" is an exact name and does not include the file path.

If "regex" is given, it specifies a regex that must matched with in the file name (not including the file path) to replace with "name". "name" will be used as the replacement in the "Pattern.sub" function.

If multiple files are provided in "src", the "failed" list (accessible through failed()) is set to a list of files and folders that failed to be renamed.



## Clipboard-Like Operations

### cut
**cut(\*src: Union[str, os.PathLike, Iterable[Union[str, os.PathLike]]])**

Marks a set of files and folders to be moved by paste(). Clears any marked files/folders.

### copy
**copy(\*src: Union[str, os.PathLike, Iterable[Union[str, os.PathLike]]])**

Marks a set of files and folders to be copied by paste(). Clears any marked files/folders.

### a_cut
**a_cut(\*src: Union[str, os.PathLike, Iterable[Union[str, os.PathLike]]])**

Works like cut() but doesn't unmark any already marked files/folders.

### a_copy
**a_copy(\*src: Union[str, os.PathLike, Iterable[Union[str, os.PathLike]]])**

Works like copy() but doesn't unmark any already marked files/folders.

### unmark
**unmark()**

Unmarks all marked files and folders.

### paste
**paste(dst: Union[str, os.PathLike], root: Union[str, os.PathLike] = None, force=None) -> bool**

Pastes (moves or copies) a set of files and folders into the folder "dst". All marked items will become unmarked. Non-existant marked items will be ignored. Returns True on complete success, and False on failure.

Note that

By default, the copied folders and files do not keep their parent folder structure. If "root" is provided, any marked folders and files found in the folder "root" are copied into "dst" with their folder structure under "root" ("root" is not included). Every other folder or file is copied into dst normally.

The "failed" list (accessed through failed()) is set to a list of files and folders that failed.



## Archiving Operations

### archive
**archive(src: Union[str, os.PathLike], dst: Union[str, os.PathLike] = '.', format: str = 'zip', into: bool = True, temp=False, force=None) -> str**

Archives all of the content in folder "src" into an archive and then moves the archive into "dst". Returns the path of the created archive. Note that empty folders will not be included in the archive.

By default, "dst" is treated as a folder (not a file name) to put the archive into. Parent folders will be created if they do not exist; if "into" is False, "dst" is the path and name of the new archive including the extension (which does not have to match the archive format). If "dst" already exists, it will be overwritten or merged into.

On import, this module will attempt to register the formats '7zip' (if the py7zr module is installed) and 'jar' (which is just a renamed zip file).

If "temp" is True, this function will also delete the "src" folder.

Default supported types are those supported by shutil.make_archive() (so custom formats registered through shutil.register_archive_format() work too). Note that the type does not have to match the file extension of "dst" if into is False.

### extract
**extract(src: Union[str, os.PathLike], dst: Union[str, os.PathLike] = '.', temp=False, force=None) -> bool**

Extracts the content in the archive "src" and merges it with "dst". Merges folders and overwrites files that are already in "dst". The type of the archive is assumed. The "dst" folder will be created if it does not exist. See archive() for extra added filetypes. Returns True on complete success, False on failure.

If "temp" is True, this function will also delete the "src" archive.

Supported file types are those supported by shutil.unpack_archive().

Sets "failed" to a list of failed items that could not be extracted. Note that these failed paths will have a random uuid in them.


