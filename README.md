# lvconfig

Typed reader and writer for LabVIEW configuration files, with LabVIEW-correct escaping, path and boolean rules.

## Install

```
pip install lvconfig
```

## Usage

```python
import lvconfig

text = """
; rig configuration
[General]
name = "Rig \\22A\\22"
enabled = TRUE
retries = 3

[Paths]
log = "/C/Temp/log.txt"
"""

config = lvconfig.parse(text)

config.get_str("General", "name")      # 'Rig "A"'   (quotes decoded from \22)
config.get_bool("General", "enabled")  # True
config.get_int("General", "retries")   # 3
config.get_path("Paths", "log")        # 'C:\\Temp\\log.txt'

# Build and write a file LabVIEW reads back correctly.
out = lvconfig.Config()
out.set("General", "name", 'Rig "A"\r')            # quoted and escaped on dump
out.set("General", "enabled", True)                # written as TRUE, not "True"
out.set_path("Paths", "log", r"C:\Temp\log.txt")   # stored as /C/Temp/log.txt
print(lvconfig.dump(out))
```

Read and write files directly with `load` and `save`. `save` uses the `CRLF` line
endings LabVIEW writes on Windows:

```python
config = lvconfig.load("settings.ini")
config.set("General", "retries", 5)
lvconfig.save(config, "settings.ini")
```

Comments survive a round-trip. `parse` keeps every whole-line `;` comment and attaches
it to the section or key below it, and `dump` writes it back. `Config` also offers
`items`, `to_dict`, `remove` and `remove_section`.

Low-level helpers are public too: `escape`/`unescape` for the `\XX` codes,
`to_labview_path`/`from_labview_path` for the stored path form, and
`to_bool`/`to_int`/`to_float` for value coercion.

## Command line

Installing the package puts an `lvconfig` command on the path:

```
lvconfig json settings.ini                         # dump the file as decoded JSON
lvconfig json settings.ini --section General        # only one section
lvconfig get settings.ini General enabled --type bool
lvconfig get settings.ini Paths log --type path     # prints C:\Temp\log.txt
lvconfig convert plain.ini labview.ini              # plain .ini to LabVIEW-escaped form
```

`convert` reads a plain INI (the kind `configparser` writes), infers booleans and
numbers, and writes it back with LabVIEW escaping, quoting and path form. Run
`lvconfig --help` for the full list with examples.

## Escaping rules it handles

- `\XX` hex codes for control and non-displayable characters (a carriage return is
  `\0D`, a tab is `\09`), decoded on read and re-encoded on write with uppercase digits.
- Doubled backslashes: a literal backslash is stored as `\\`.
- Quoted strings: string and path values are wrapped in double quotes to protect
  surrounding whitespace, and the quotes come off on read.
- Stored paths: the drive letter moves after a leading slash and separators become
  forward slashes, so `C:\Temp\log.txt` is stored as `/C/Temp/log.txt`; UNC paths keep a
  leading `//`.
- Booleans as `TRUE`/`FALSE`, with `1`/`0` also read as booleans.

## Why

LabVIEW's "Configuration File" format looks like an INI file but is not one. LabVIEW's
own Configuration File VIs, and the OpenG Variant Configuration File library on top of them,
encode control characters as `\XX` hex codes (a carriage
return is `\0D`), double literal backslashes, wrap string and path values in quotation
marks to protect whitespace, store paths in a platform-neutral form with the drive
after a leading slash (`C:\Temp` becomes `/C/Temp`), and write booleans as `TRUE` or
`FALSE`. These rules are described in NI's [Windows configuration settings file
format](https://www.ni.com/docs/en-US/bundle/labview/page/windows-configuration-settings-file-format.html)
documentation. All of that runs inside LabVIEW; none of it helps a Python process with no
LabVIEW present.

Python's standard-library `configparser` honours none of them: it does not decode
`\XX` escapes, treats backslashes literally, keeps the surrounding quotation marks as
part of the value, and leaves `/C/Temp` as a broken path. The result is a corrupted
read and a file LabVIEW cannot load back. This is a long-standing pain point in the NI
community (for example the "ConfigFile Read Key" doubled-backslash reports on
forums.ni.com), and at the time of writing no maintained PyPI package implements these
semantics: the available INI parsers (`configparser`, `iniparse`, `iniparser2`) are all
generic and share the same gap.

`lvconfig` reads and writes the format exactly as LabVIEW does, round-trips losslessly,
and coerces each value to the Python type it stands for. It is pure standard library,
fully typed, and ships `py.typed`.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
