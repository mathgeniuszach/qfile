from qfile import *

from pathlib import Path

import re

# Test the library (This was really annoying to make but necessary)
def _test():
    """Tests this library. If any error is raised then something is at fault."""
    # Temp folder
    name = uuid()
    with wd(name):
        # Test temp dir
        with wd("temp", temp=True):
            pass
        assert not exists("temp")

        # Test write/read
        with wd("fs"):
            text = "rawtext"
            raw = b"stuff"
            linedata = ["text", "textb", "textc", "   "]
            table = [["a", "b", "c"], ["x", "y", "z"]]
            jdata = {"a": 1, "b": {"c": 2}}
            pdata = ["a", 1, uuid]

            # Write
            write("empty.txt", "asdfasdf")
            write("empty.txt")
            write("text.txt", text)
            write("bytes.dat", raw)
            write("lines.txt", linedata)
            write("table.csv", table, "t")
            write("data.json", jdata, "j")
            write("pickle.dat", pdata, "p")

            # Read
            assert read("empty.txt") == ""
            assert read("text.txt") == text
            assert read("bytes.dat", "b") == raw
            assert read("lines.txt", "l") == linedata
            assert read("table.csv", "t") == table
            assert read("data.json", "j") == jdata
            assert read("pickle.dat", "p") == pdata

            read("non.txt", err="potato")
            assert read("non.txt") == "potato"

            # Chunks and lines
            assert list(chunks("bytes.dat", 3)) == [b'stu', b'ff']
            assert list(lines("lines.txt", empty=False, strip=True)) == linedata[:3]
            assert list(lines("lines.txt")) == linedata

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
        with force(False):
            # Clone function
            try:
                clone("h", "o.txt")
                assert False, "cloned folder to file"
            except OSError:
                pass
            # Move function
            try:
                move("o.txt", "h")
                assert False, "moved file to folder"
            except OSError:
                pass
            # Folder function
            try:
                folder("o.txt")
                assert False, "made folder at file"
            except OSError:
                pass
            # Touch function
            try:
                touch("h")
                assert False, "made file at folder"
            except OSError:
                pass
            # Write function
            try:
                write("h", "lol")
                assert False, "wrote to folder"
            except OSError:
                pass
            # Read function
            try:
                read("h", err=True)
                assert False, "read from folder"
            except OSError:
                pass

        with force():
            folder("y")
            write("y", "text")
            assert isfile("y")
            clone("h", "y")
            assert isdir("y")
            write("y", "text")
            assert isfile("y")
            move("h", "y")
            assert isdir("y")

        # Print success message
        print("Tests succeeded")

    # input("Press enter to exit...")
    delete(name)

if __name__ == "__main__":
    _test()