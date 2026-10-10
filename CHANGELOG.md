# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- `parse` and `dump` for LabVIEW configuration text, preserving section and key order.
- `Config` container with typed getters and setters (`get_str`, `get_bool`, `get_int`,
  `get_float`, `get_path`, `set`, `set_path`).
- LabVIEW-correct `escape`/`unescape` for `\XX` hex codes and doubled backslashes.
- `to_labview_path`/`from_labview_path` for the platform-neutral stored path form.
- `to_bool`/`to_int`/`to_float` value coercion, including `TRUE`/`FALSE`/`0`/`1`.
- First release.
