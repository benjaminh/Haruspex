#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gui.Haruspex import Haruspex
from PyQt5.QtWidgets import QApplication
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    haruspex = Haruspex()
    app.exec()
