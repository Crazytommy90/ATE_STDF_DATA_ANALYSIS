#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : ui_unit_chart.py
@Author  : Link
@Time    : 2023/1/2 12:32
@Mark    : 
"""
import datetime as dt

from PySide2 import QtGui
from PySide2.QtCore import Slot, Qt
from PySide2.QtGui import QGuiApplication, QKeyEvent
from PySide2.QtWidgets import QWidget, QVBoxLayout, QAction

from ui_component.ui_app_variable import UiGlobalVariable, QtPlotAllUse


class UnitChartWindow(QWidget):
    key: int = None
    p_range = None
    change = False

    def __init__(self, parent=None):
        super(UnitChartWindow, self).__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        # This action is used for state by child classes (like TransBarChart),
        # but it is not added to any visible toolbar here.
        # The parent (MultiChartWindow) is responsible for the toolbar.
        self.action_signal_binding = QAction("signal_binding", self)
        self.action_signal_binding.setCheckable(True)
        self.action_signal_binding.setChecked(True)

    def set_data(self, key: int):
        self.key = key
        # QWidget does not have a window title to set. The title is handled by the dock.

    def set_resize_update(self, width, height):
        """This method is called by the parent (MultiChartWindow) to resize this chart."""
        self.setFixedSize(width, height)

    def setCentralWidget(self, widget):
        """This method is called by child classes like TransBarChart to add the plot widget."""
        self.layout().addWidget(widget)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Control:
            QtPlotAllUse.MultiSelect = True
        super(UnitChartWindow, self).keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Control:
            QtPlotAllUse.MultiSelect = False
        super(UnitChartWindow, self).keyReleaseEvent(event)
