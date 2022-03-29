# -*- coding: utf-8 -*-
import os
import shutil
import pathlib
import tempfile


def atomic_write(f: pathlib.Path, content: bytes | str) -> None:
    mode = 'w' if isinstance(content, str) else 'wb'
    tmp_file = tempfile.NamedTemporaryFile(mode, delete=False)
    try:
        tmp_name = tmp_file.name
        tmp_file.write(content)
    except:
        tmp_file.close()
        os.remove(tmp_name)
        raise
    tmp_file.close()
    shutil.move(tmp_name, f)
