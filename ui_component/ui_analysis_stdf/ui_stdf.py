#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : ui_stdf.py
@Author  : Link
@Time    : 2022/5/2 10:44
@Mark    : 
"""
import math
import sys
import datetime as dt
from typing import Union, List
from pydoc import help

import numpy as np
import pandas as pd
from PySide2.QtCore import Slot, QTimer, Qt, Signal
from PySide2.QtGui import QCloseEvent
from PySide2.QtWidgets import QMainWindow, QApplication, QWidget, QMessageBox

from pyqtgraph.dockarea import *

from chart_core.chart_pyqtgraph.core.mixin import ChartType
from chart_core.chart_pyqtgraph.poll import ChartDockWindow
from common.li import Li, SummaryCore
from ui_component.ui_analysis_stdf.ui_components.ui_data_group import DataGroupWidget
from ui_component.ui_common.ui_console import ConsoleWidget
from ui_component.ui_analysis_stdf.ui_designer.ui_home_load import Ui_MainWindow
from ui_component.ui_common.ui_utils import QTableUtils
from ui_component.ui_analysis_stdf.ui_components.ui_file_load_widget import FileLoadWidget  # 文件选取
from ui_component.ui_analysis_stdf.ui_components.ui_tree_load_widget import TreeLoadWidget  # 载入的数据选取
from ui_component.ui_analysis_stdf.ui_components.ui_table_load_widget import TableLoadWidget  # 测试项选取


class StdfLoadUi(QMainWindow, Ui_MainWindow):
    """
    懒加载界面
    """
    closeSignal = Signal(int)
    parent = None

    def __init__(self, parent=None, space_nm=1, path_select=False, select=True, is_web=False):
        super(StdfLoadUi, self).__init__(parent)
        self.setupUi(self)
        self.space_nm = space_nm
        self.li = Li()
        self.summary = SummaryCore()
        self.title = "STDF数据载入空间: {}".format(space_nm)
        self.setWindowTitle(self.title)

        self.area = DockArea()
        self.setCentralWidget(self.area)
        " FileLoadWidget用来载入数据文件，内部用到多线程 "
        self.stdf_select_widget = FileLoadWidget(self.summary, self, space_nm=space_nm)
        self.dock_stdf_load = Dock("STDF File Select", size=(400, 100))
        self.dock_stdf_load.addWidget(self.stdf_select_widget)
        self.area.addDock(self.dock_stdf_load)

        " TreeLoadWidget用来载入和配对内部数据，会占用到大量的IO资源 "
        self.tree_load_widget = TreeLoadWidget(self.li, self.summary, self)
        dock_tree_load = Dock("Data Tree Select & Config", size=(200, 300))
        dock_tree_load.addWidget(self.tree_load_widget)
        self.area.addDock(dock_tree_load, "bottom", self.dock_stdf_load)
        # self.area.moveDock(self.dock_stdf_load, 'above', dock_tree_load)

        " TableLoadWidget用来载入和配对内部数据，会占用到大量的IO资源, 并且是作为主要的分析界面 "
        self.table_load_widget = TableLoadWidget(self.li, self.summary, self)
        dock_table_load = Dock("Data TEST NO&ITEM Analysis", size=(200, 300))
        dock_table_load.addWidget(self.table_load_widget)
        self.area.addDock(dock_table_load, "right", dock_tree_load)
        # self.area.moveDock(dock_tree_load, 'above', dock_table_load)

        " DataGroupWidget用来对数据进行简单的分组和筛选 "
        self.group_table_widget = DataGroupWidget(self.li)
        dock_group_load = Dock("Data Group", size=(50, 300))
        dock_group_load.addWidget(self.group_table_widget)
        self.area.addDock(dock_group_load)

        text = """
        载入的功能包: np(numpy), pd(pandas), math
        载入的数据:
            点击RUN后会被刷新 
            li: 数据空间的集合数据, 通过help(li)查看
        RUN.
        """
        self.namespace = {
            "np": np,
            "pd": pd,
            "math": math,
            "help": help,
            "li": self.li,
            "summary": self.summary
        }
        self.console = ConsoleWidget(parent=self, namespace=self.namespace, text=text)
        self.dock_console_load = Dock("Python Console", size=(400, 100))
        self.dock_console_load.addWidget(self.console)
        self.area.addDock(self.dock_console_load, "bottom")
        # self.area.moveDock(self.dock_stdf_load, 'above', dock_console_load)
        "------------------------------------------------------------------------------"
        self.area.restoreState(
            {
                'main': (
                    'horizontal',
                    [
                        ('dock', 'Data Group', {}),
                        ('vertical',
                         [('horizontal', [
                             (
                                 'vertical',
                                 [
                                     (
                                         'dock',
                                         'STDF File Select',
                                         {}
                                     ),
                                     ('dock',
                                      'Data Tree Select & Config',
                                      {}
                                      )
                                 ],
                                 {
                                     'sizes': [147, 198]
                                 }
                             ),
                             (
                                 'dock',
                                 'Python Console',
                                 {})],
                           {'sizes': [737, 429]}),
                          ('dock',
                           'Data TEST NO&ITEM Analysis',
                           {})],
                         {'sizes': [350, 439]})],
                    {'sizes': [372, 1171]}), 'float': []})
        self.dock_console_load.hide()  # 可以显示和隐藏
        self.init_signal()

        " 用来存放chart的 "
        self.chart_ui = ChartDockWindow(self.li, None, icon=None, space_nm=space_nm, summary=self.summary)  # type:ChartDockWindow

        if select and is_web is False:
            if path_select:
                self.stdf_select_widget.first_directory_select()
            else:
                self.stdf_select_widget.first_select()

    def init_signal(self):
        self.stdf_select_widget.finished.connect(self.tree_load_widget.set_tree)
        self.li.QCalculation.connect(self.q_calculation)
        self.li.QMessage.connect(self.message_show)
        self.li.QStatusMessage.connect(self.mdi_space_message_emit)

    def q_calculation(self):
        self.table_load_widget.cal_table()
        self.group_table_widget.checkbox_changed()

    @Slot(SummaryCore)
    def merge_data_emit(self, data: SummaryCore):
        self.summary = data
        self.tree_load_widget.set_tree()

    @Slot()
    def on_action_dock_structure_triggered(self):
        """ 将 area 布局保存在泡菜中 """
        state = self.area.saveState()
        print(state)

    @Slot()
    def on_action_sava_data_triggered(self):
        """ 将数据保存在csv文件中 """
        if self.li.df_module is None:
            self.mdi_space_message_emit("请先将数据载入到数据空间中!")
            return

        from PySide2.QtWidgets import QFileDialog, QMessageBox
        import os

        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存数据为CSV文件",
            f"STDF_Data_{self.space_nm}.csv",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        try:
            # 根据文件扩展名决定保存格式
            if file_path.endswith('.xlsx'):
                self.save_data_to_excel(file_path)
            else:
                self.save_data_to_csv(file_path)

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"数据保存失败: {str(e)}")

    def save_data_to_csv(self, file_path):
        """保存数据到CSV文件"""
        # 保存制程能力数据
        if self.li.capability_key_list:
            capability_df = pd.DataFrame(self.li.capability_key_list)
            capability_path = file_path.replace('.csv', '_capability.csv')
            capability_df.to_csv(capability_path, encoding='utf-8-sig', index=False)
            self.mdi_space_message_emit(f"制程能力数据已保存: {capability_path}")

        # 保存原始测试数据
        if self.li.to_chart_csv_data and self.li.to_chart_csv_data.df is not None:
            test_data_path = file_path.replace('.csv', '_test_data.csv')
            self.li.to_chart_csv_data.df.to_csv(test_data_path, encoding='utf-8-sig')
            self.mdi_space_message_emit(f"测试数据已保存: {test_data_path}")

        # 保存汇总信息
        if self.li.select_summary is not None:
            summary_path = file_path.replace('.csv', '_summary.csv')
            self.li.select_summary.to_csv(summary_path, encoding='utf-8-sig', index=False)
            self.mdi_space_message_emit(f"汇总信息已保存: {summary_path}")

    def save_data_to_excel(self, file_path):
        """保存数据到Excel文件"""
        import pandas as pd

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # 保存制程能力数据
            if self.li.capability_key_list:
                capability_df = pd.DataFrame(self.li.capability_key_list)
                capability_df.to_excel(writer, sheet_name='制程能力', index=False)

            # 保存测试数据
            if self.li.to_chart_csv_data and self.li.to_chart_csv_data.df is not None:
                # 限制数据量，避免Excel文件过大
                test_df = self.li.to_chart_csv_data.df
                if len(test_df) > 100000:  # 如果数据量太大，只保存前10万行
                    test_df = test_df.head(100000)
                    self.mdi_space_message_emit("测试数据量较大，仅保存前10万行")
                test_df.to_excel(writer, sheet_name='测试数据')

            # 保存汇总信息
            if self.li.select_summary is not None:
                self.li.select_summary.to_excel(writer, sheet_name='汇总信息', index=False)

            # 保存Top Fail信息
            if self.li.top_fail_dict:
                top_fail_df = pd.DataFrame([
                    {'TEST_ID': k, 'FAIL_COUNT': v}
                    for k, v in self.li.top_fail_dict.items()
                ])
                top_fail_df.to_excel(writer, sheet_name='Top_Fail', index=False)

        self.mdi_space_message_emit(f"Excel文件已保存: {file_path}")

    @Slot()
    def on_action_console_triggered(self):
        if self.action_console.isChecked():
            self.dock_console_load.show()
        else:
            self.dock_console_load.hide()

    @Slot()
    def on_action_limit_triggered(self):
        self.li.show_limit_diff()

    @Slot(str)
    def mdi_space_message_emit(self, message: str):
        """
        append message
        :param message:
        :return:
        """
        self.statusbar.showMessage("==={}==={}===".format(dt.datetime.now().strftime("%H:%M:%S"), message))

    def message_show(self, text: str) -> bool:
        res = QMessageBox.question(self, '待确认', text,
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.Yes)
        if res == QMessageBox.Yes:
            return True
        else:
            return False

    def get_test_id_column(self) -> Union[List[int], None]:
        """

        :return:
        """
        return QTableUtils.get_table_widget_test_id(self.table_load_widget.cpk_info_table)

    def get_text_column(self) -> Union[List[str], None]:
        """

        :return:
        """
        test_id_column = self.get_test_id_column()
        if not test_id_column:
            return None
        text_column = []
        for each in test_id_column:
            table_row = self.li.capability_key_dict[each]
            text = str(table_row["TEST_NUM"]) + ":" + table_row["TEST_TXT"]
            text_column.append(text)
        return text_column

    @Slot()
    def on_action_qt_distribution_trans_triggered(self):
        """ 使用PYQT来拉出横向柱状分布图 """
        test_id_column: List[int] = self.get_test_id_column()
        self.chart_ui.add_chart_dock(test_id_column, ChartType.TransBar)
        self.chart_ui.show()
        self.chart_ui.raise_()

    @Slot()
    def on_action_qt_scatter_triggered(self):
        """ 使用PYQT来拉出线性散点图 """
        test_id_column: List[int] = self.get_test_id_column()
        self.chart_ui.add_chart_dock(test_id_column, ChartType.TransScatter)
        self.chart_ui.show()
        self.chart_ui.raise_()

    @Slot()
    def on_action_qt_mapping_triggered(self):
        """ 使用PYQT来拉出Mapping图 """
        test_id_column: List[int] = self.get_test_id_column()
        self.chart_ui.add_chart_dock(test_id_column, ChartType.Mapping)
        self.chart_ui.show()
        self.chart_ui.raise_()

    @Slot()
    def on_action_qt_visual_map_triggered(self):
        """ 使用PYQT来拉出Visual Map图 """
        test_id_column = self.get_test_id_column()
        self.chart_ui.add_chart_dock(test_id_column, ChartType.VisualMap)
        self.chart_ui.show()
        self.chart_ui.raise_()

    @Slot()
    def on_action_capability_triggered(self):
        """ 生成制程能力报告 """
        # 检查是否有数据
        if self.li.df_module is None:
            self.mdi_space_message_emit("请先加载STDF数据")
            QMessageBox.warning(self, "警告", "请先加载STDF数据后再生成制程能力报告")
            return

        # 检查是否已计算制程能力
        if self.li.capability_key_list is None or len(self.li.capability_key_list) == 0:
            self.mdi_space_message_emit("制程能力数据未计算，请先选择数据并计算")
            QMessageBox.warning(self, "警告", "请先在数据表格中选择数据并计算制程能力")
            return

        # 显示制程能力报告
        self.chart_ui.show_capability_report()
        self.chart_ui.show()
        self.chart_ui.raise_()

    @Slot()
    def on_action_summary_triggered(self):
        """ 生成Summary报告 """
        # 检查是否有数据
        if self.li.df_module is None or self.summary.summary_df is None:
            self.mdi_space_message_emit("请先加载STDF数据")
            QMessageBox.warning(self, "警告", "请先加载STDF数据后再生成Summary报告")
            return

        # 更新chart_ui的summary引用（确保使用最新的summary数据）
        self.chart_ui.summary = self.summary

        # 添加Summary Dock
        success = self.chart_ui.add_summary_dock()

        if success:
            self.chart_ui.show()
            self.chart_ui.raise_()
            self.mdi_space_message_emit("Summary报告已生成")
        else:
            self.mdi_space_message_emit("Summary报告生成失败")

    def closeEvent(self, a0: QCloseEvent) -> None:
        """
        删除mdi时, 需要将与其对应的chart也删除
        """
        self.closeSignal.emit(self.space_nm)
        return super(StdfLoadUi, self).closeEvent(a0)
