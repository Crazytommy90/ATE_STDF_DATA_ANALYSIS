#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : poll.py
@Author  : Link
@Time    : 2022/6/4 14:40
@Mark    : 
"""
from typing import List

from PySide2.QtCore import Signal
from PySide2.QtWidgets import QMainWindow
from pyqtgraph.dockarea import DockArea, Dock

from chart_core.chart_pyqtgraph.core.mixin import ChartType
from chart_core.chart_pyqtgraph.ui_components.ui_multi_chart import MultiChartWindow
from chart_core.chart_pyqtgraph.ui_designer.ui_chart_window import Ui_MainWindow
from common.li import Li, SummaryCore
from ui_component.ui_common.my_text_browser import Print


class MyDock(Dock):
    closeSignal = Signal(object)

    def close(self):
        super(MyDock, self).close()
        Print.warning("Dock Close")
        self.widgets = None
        MultiChartWindow.clearLayout(self.layout)
        self.closeSignal.emit(self.name())


class ChartDockWindow(QMainWindow, Ui_MainWindow):
    """
    停靠ChartsUi
    TODO:
        1. 一个MDI只有一个ChartDockWindow
        2. 提前规划好
    """
    add_position = "right"
    charts = 0

    def __init__(self, li: Li, parent=None, icon=None, space_nm=1, summary: SummaryCore = None):
        super(ChartDockWindow, self).__init__(parent)
        self.setupUi(self)
        self.li = li
        self.summary = summary
        self.parent = parent
        self.space_nm = space_nm
        if icon is not None:
            self.setWindowIcon(icon)
        self.title = "载入空间: {} -> Chart Widget".format(space_nm)
        self.setWindowTitle(self.title)
        self.area = DockArea()
        self.setCentralWidget(self.area)

    def add_dock(self, dock):
        if dock is None:
            return False
        dock.closeSignal.connect(self.closeDock)
        self.area.addDock(dock, self.add_position)
        if self.add_position == "right":
            self.add_position = "bottom"
        else:
            self.add_position = "right"
        return True

    def add_chart_dock(self, test_id_list: List[int], chart_type: ChartType):
        """
        TODO: Data Dock 待添加
        :param test_id_list:
        :param chart_type:
        :return:
        """
        dock = None
        self.charts += 1
        if chart_type == ChartType.TransBar:
            bar_chart = MultiChartWindow(self.li)
            bar_chart.set_data(test_id_list, chart_type)
            dock = MyDock("横向分布图_{}".format(self.charts), size=(400, 400), closable=True)
            dock.addWidget(bar_chart)
        if chart_type == ChartType.TransScatter:
            scatter_chart = MultiChartWindow(self.li)
            scatter_chart.set_data(test_id_list, chart_type)
            dock = MyDock("横向分布图_{}".format(self.charts), size=(400, 400), closable=True)
            dock.addWidget(scatter_chart)
        if chart_type == ChartType.VisualMap:
            visual_map_chart = MultiChartWindow(self.li)
            visual_map_chart.set_data(test_id_list, chart_type)
            dock = MyDock("参数性Map_{}".format(self.charts), size=(400, 400), closable=True)
            dock.addWidget(visual_map_chart)
        if chart_type == ChartType.Mapping:
            mapping_chart = MultiChartWindow(self.li)
            mapping_chart.set_data(test_id_list, chart_type)
            dock = MyDock("Mapping图_{}".format(self.charts), size=(600, 500), closable=True)
            dock.addWidget(mapping_chart)
        return self.add_dock(dock)

    def add_summary_dock(self):
        """
        添加Summary Dock
        :return: 是否成功添加
        """
        from ui_component.ui_analysis_stdf.ui_components.ui_summary_widget import SummaryWidget

        if self.summary is None:
            Print.warning("Summary数据未初始化")
            return False

        self.charts += 1
        summary_widget = SummaryWidget(self.li, self.summary)
        summary_widget.generate_summaries()

        dock = MyDock("Summary报告_{}".format(self.charts), size=(800, 600), closable=True)
        dock.addWidget(summary_widget)

        return self.add_dock(dock)

    def show_capability_report(self):
        """
        显示制程能力报告
        :return: 是否成功添加
        """
        from ui_component.ui_analysis_stdf.ui_components.ui_capability_widget import CapabilityWidget

        if self.li is None:
            Print.warning("Li数据未初始化")
            return False

        if self.li.capability_key_list is None or len(self.li.capability_key_list) == 0:
            Print.warning("制程能力数据未计算，请先加载数据并计算")
            return False

        self.charts += 1
        capability_widget = CapabilityWidget(self.li, self)

        dock = MyDock("制程能力报告_{}".format(self.charts), size=(1000, 800), closable=True)
        dock.addWidget(capability_widget)

        return self.add_dock(dock)

    def closeDock(self, dock_name):
        del self.area.docks[dock_name]