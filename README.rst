PyPPMd-Gentee
=============

A fork of `pyppmd <https://github.com/miurahr/pyppmd>`_ that adds the Gentee PPMd-I
variant decoder (``Ppmd8gDecoder``). Installable alongside the official ``pyppmd`` package.

Install with ``pip install pyppmd-gentee``, then ``import pyppmd_gentee``.


Introduction
------------

``pyppmd_gentee`` provides the same classes and functions as ``pyppmd`` for compressing
and decompressing data using the PPMd algorithm, plus ``Ppmd8gDecoder`` — a variant
of PPMd-I that implements the Gentee installer's modified codec.


Development status
------------------

A project status is considered as ``Stable``.

Gentee PPMd-I variant
---------------------

``Ppmd8gDecoder`` decodes data compressed with the PPMd variant used in Gentee installers.
It differs from the standard PPMd-I codec in BinSumm initialization, frequency updates,
and model restore behaviour.

.. code-block:: python

    import pyppmd_gentee

    dec = pyppmd_gentee.Ppmd8gDecoder(max_order=6, mem_size=16 << 20)
    result = dec.decode(compressed_data, expected_length)

For streaming across multiple files (as in GEA archives), use ``lightweight_reset()``
or ``reinit()`` between entries to manage the decoder state:

.. code-block:: python

    dec = pyppmd_gentee.Ppmd8gDecoder(max_order=6, mem_size=16 << 20)

    first_file = dec.decode(chunk_0, length_0)

    dec.lightweight_reset()  # keeps model, resets context to root
    second_file = dec.decode(chunk_1, length_1)

    dec.reinit(6)  # full model rebuild
    third_file = dec.decode(chunk_2, length_2)

See ``examples/extract_stardef.py`` for a complete example that downloads and extracts
a Gentee-based installer using ``Ppmd8gDecoder``.

Extra input byte
----------------

``PPMd`` algorithm and implementation is designed to use ``Extra`` input byte.
The encoder will omit a last null (b"\0") byte when last byte is b"\0".
You may need to provide an extra null byte when you don't get expected size of
extracted data.

You can do like as:

.. code-block::

    dec = pyppmd.Ppmd7Decoder(max_order=6, mem_size=16 << 10)
    result = dec.decode(compressed, length)
    if len(result) < length:
        if dec.needs_input:
            # ppmd need an extra null byte
            result += dec.decode(b"\0", length - len(result))
        else:
            result += dec.decode(b"", length - len(result))


.. warning::
   When use it on MSYS2/MINGW64 environment, you should set environment variable ``SETUPTOOLS_USE_DISTUTILS=stdlib``

Copyright and License
---------------------

Some codes are derived from p7zip/7zip and pyzstd project.
Details are shown in LicenseNotices.rst

- SPDX-License-Identifier: LGPL-2.1-or-later
- SPDX-URL: https://spdx.org/licenses/LGPL-2.1-or-later.html

PyPPMd is licensed under GNU Lesser General Public License v2.1 or later.

- Copyright (C) 2020-2025 Hiroshi Miura
- Copyright (C) 2020-2021 Ma Lin
- Copyright (C) 2010-2012 Lockless Inc.
- Copyright (C) 1999-2017 Igor Pavlov

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
