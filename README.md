# qfile
A python library for simplifying common file operations.

`pip install qfile`

Common file operations in python should be simpler and involve less boilerplate, while still delivering fairly powerful options.
qfile was created for just that purpose.

Some simple code examples:
```python
import qfile

# Write to a given file
qfile.write("text.txt", "my text here")

# Read the given file
text = qfile.read("text.txt") # text == "my text here"

# Move folder "a" to existing folder "b", merging it with "b" if it already exists
qfile.move("a", "b", force=True) # Setting force=True ensures files replace folders with the same name in "b".

# Rename folder/file "x" to "y", raising an error if "y" exists already
qfile.rename("x", "y")

# Clone folder "b" into folder "c", making folder "c" if it doesn't exist
qfile.clone("b", "c", into=True)

# Make a folder, not caring if it already exists
# The same as Path("x/y/z").mkdir(parents=True, exist_ok=True) or os.makedirs(exist_ok=True)
qfile.folder("x/y/z")

# Delete the folder or file named "deleteme"
qfile.delete("deleteme")

# Replace all instances of "old" with "new" in all the ".txt" files in the current working directory
qfile.replace(qfile.glob(".", "**/*.txt"), "old", "new")
```

qfile can do a whole lot more, just check out the [API documentation](API.md)

## Deeper Example

Here's a specific example task: let's say you wanted to write some code that does these things:
- Open up an directory given by the user (creating it if it doesn't exist)
- Write a dictionary to a file in that directory in json-based format
- Read from a file in that directory, and if that file does not exist, use some other default value instead, writing back to the file
- Delete the file/folder "deleteme" in that directory, regardless of if it is a folder or a file with no extension. Nothing should happen if the item doesn't exist.

Someone might write code to do this like so:
```python
from pathlib import Path
import json
import shutil

# Make the directory
path = Path(input("Enter a directory: "))
path.mkdir(parents=True, exist_ok=True)
# Write dictionary to file
path.join("data.json").write_text(json.dumps({"a": 1, "b": 2}))

# Read from file
file = path.join("text")
try:
    text = file.read_text("utf-8")
except FileNotFoundError:
    text = "default"
    file.write_text(text, "utf-8")

# Delete "deleteme"
badfile = path.join("deleteme")
if badfile.is_dir():
    shutil.rmtree(badfile)
elif badfile.is_file():
    os.remove(badfile)
```

qfile, at least in my opinion, makes this process much simpler and more readable:
```python
import qfile

path = input("Enter a directory")
# Make the directory
with qfile.wd(path):
    # Write dictionary to file
    qfile.write("data.json", {"a": 1, "b": 2}, 'j')
    
    # Read from file
    text = qfile.read("text.txt", err="default")
    
    # Delete "deleteme"
    qfile.delete("deleteme")
```
