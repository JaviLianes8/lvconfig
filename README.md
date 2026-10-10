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
[General]
name = "Rig \\22A\\22"
enabled = TRUE
retries = 3

[Paths]
log = "/C/Temp/log.txt"
"""

config = lvconfig.parse(text)

config.get_str("General", "name")     # 'Rig "A"'   (quotes decoded from \22)
config.get_bool("General", "enabled")  # True
config.get_int("General", "retries")   # 3
config.get_path("Paths", "log")        # 'C:\\Temp\\log.txt'

# Build and write a file LabVIEW reads back correctly.
out = lvconfig.Config()
out.set("General", "name", 'Rig "A"\r')   # quoted and escaped on dump
out.set("General", "enabled", True)        # written as TRUE, not "True"
out.set_path("Paths", "log", r"C:\Temp\log.txt")  # stored as /C/Temp/log.txt
print(lvconfig.dump(out))
```

Low-level helpers are public too: `escape`/`unescape` for the `\XX` codes,
`to_labview_path`/`from_labview_path` for the stored path form, and
`to_bool`/`to_int`/`to_float` for value coercion.

## Why

LabVIEW's "Configuration File" format looks like an INI file but follows its own
escaping, quoting, path and boolean rules that Python's `configparser` corrupts.
`lvconfig` reads and writes it exactly as LabVIEW does. See the full rationale below.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
