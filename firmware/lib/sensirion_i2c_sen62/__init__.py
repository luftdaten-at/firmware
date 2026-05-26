#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Note: no ``from __future__ import`` — not supported on CircuitPython.
from .version import version as __version__  # noqa: F401

from sensirion_i2c_sen62.device import Sen62Device  # noqa: F401

__all__ = ['Sen62Device']
