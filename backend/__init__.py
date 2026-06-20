"""Backend application package."""

# Many agents emit progress logs containing non-ASCII/emoji characters. On
# Windows the console/stdout often defaults to cp1252, which raises
# UnicodeEncodeError on those prints and can crash an otherwise healthy request.
# Reconfigure stdio to UTF-8 with replacement so logging never crashes the
# pipeline. Guarded for environments where the streams aren't reconfigurable
# (e.g. some test capture harnesses).
import sys as _sys

for _stream in ("stdout", "stderr"):
    _s = getattr(_sys, _stream, None)
    _reconfigure = getattr(_s, "reconfigure", None)
    if _reconfigure is not None:
        try:
            _reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
