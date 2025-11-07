"""
-*- coding: utf-8 -*-
@Author  : Link
@Time    : 2022/5/9 17:45
@Software: PyCharm
@File    : ui_table_load_widget.py
@Remark  : 
"""
from PySide2.QtCore import Slot, Qt, QTimer
from PySide2.QtGui import QColor, QFont
from PySide2.QtWidgets import QWidget, QAbstractItemView, QTableWidget, QMessageBox

from common.app_variable import GlobalVariable
from common.li import Li, SummaryCore
from ui_component.ui_analysis_stdf.ui_designer.ui_table_load import Ui_Form as TableLoadForm
from ui_component.ui_common.ui_utils import QTableUtils, QWidgetUtils
from ui_component.ui_module.table_module import PauseTableWidget

import pyqtgraph as pg

pg.setConfigOptions(antialias=True)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class TableLoadWidget(QWidget, TableLoadForm):
    """
    Table
    .setFont(QFont(None, 8));
    .resizeRowsToContents()
    """
    li: Li = None
    summary: SummaryCore = None

    def __init__(self, li: Li, summary: SummaryCore, parent=None):
        super(TableLoadWidget, self).__init__(parent)
        self.setupUi(self)
        self.li = li
        self.summary = summary
        self.setWindowTitle("Data TEST NO&ITEM Analysis")
        self.cpk_info_table = PauseTableWidget(self)  # type:QTableWidget
        self.cpk_info_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.cpk_info_table.setEditable(True)
        # self.cpk_info_table.setFont(QFont("", 8))
        # self.cpk_info_table.horizontalHeader().sectionResized.connect(self.get_head_resize)
        self.horizontalLayout.addWidget(self.cpk_info_table)
        self.gw = pg.GraphicsLayoutWidget()
        self.gw.ci.setContentsMargins(0, 0, 0, 0)
        self.plot = self.gw.addPlot()
        self.horizontalLayout.addWidget(self.gw)
        self.init_plot()
        self.init_table_signal()
        
        # 添加清空按钮
        from PySide2.QtWidgets import QPushButton
        self.btn_clear_table = QPushButton("清空")
        self.btn_clear_table.clicked.connect(self.clear_table_data)
        self.horizontalLayout_2.insertWidget(3, self.btn_clear_table)

    def init_plot(self):
        self.gw.setMaximumWidth(20)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.setXRange(-0.2, 2.6)
        self.plot.showAxis('bottom', False)
        self.plot.showAxis('left', False)
        self.plot.hideButtons()

    def init_table_signal(self):
        """
        监控排序信号, 数据载入后会自动排序
        :return:
        """
        self.cpk_info_table.horizontalHeader().sortIndicatorChanged.connect(self.plot_scrollbar)

    def cal_table(self):
        if self.li.capability_key_list is None:
            return
        self.cpk_info_table.setData(self.li.capability_key_list)
        self.cpk_info_table.sortByColumn(GlobalVariable.TEST_ID_COLUMN, Qt.SortOrder.AscendingOrder)
        QWidgetUtils.widget_change_color(widget=self, background_color="#3316C6")

        # 数据加载完成后启用按钮
        self.enable_buttons(True)

    def plot_scrollbar(self):
        """
        :return:
        """
        QTimer.singleShot(50, self.plot_points)

    def plot_points(self):
        self.plot.clear()
        length = self.cpk_info_table.rowCount()
        self.plot.setYRange(0, length)
        x, y, z, cpk_l, top_fail_l, reject_l = [], [], [], [], [], []
        
        # 动态获取列索引
        cpk_col = self.cpk_info_table.get_column_index(GlobalVariable.CPK_COLUMN_NAME)
        top_fail_col = self.cpk_info_table.get_column_index(GlobalVariable.TOP_FAIL_COLUMN_NAME)
        reject_col = self.cpk_info_table.get_column_index(GlobalVariable.REJECT_COLUMN_NAME)
        
        for index in range(length):
            cpk = float(self.cpk_info_table.item(index, cpk_col).text())
            top_fail = float(self.cpk_info_table.item(index, top_fail_col).text())
            reject = float(self.cpk_info_table.item(index, reject_col).text())
            if GlobalVariable.CPK_LO < cpk < GlobalVariable.CPK_HI:
                x.append(0)
                cpk_l.append(length - index)
                item = self.cpk_info_table.item(index, cpk_col)
                item.setBackground(QColor(250, 194, 5, 50))
            if top_fail > GlobalVariable.TOP_FAIL_LO:
                y.append(1)
                top_fail_l.append(length - index)
                item = self.cpk_info_table.item(index, top_fail_col)
                item.setBackground(QColor(217, 83, 25, 150))
            if reject > GlobalVariable.REJECT_LO:
                z.append(2)
                reject_l.append(length - index)
                item = self.cpk_info_table.item(index, reject_col)
                item.setBackground(QColor(217, 83, 25, 30))

        plot = pg.ScatterPlotItem(symbol='s', size=3, pen=None)
        plot.addPoints(x, cpk_l, pen=(250, 194, 5))
        plot.addPoints(y, top_fail_l, pen=(217, 83, 25))
        plot.addPoints(z, reject_l, pen=(217, 83, 25))
        self.plot.addItem(plot)
        self.cpk_info_table.resizeRowsToContents()

    @Slot(bool)
    def on_checkBox_clicked(self, e):
        if e:
            top_fail_col = self.cpk_info_table.get_column_index(GlobalVariable.TOP_FAIL_COLUMN_NAME)
            self.cpk_info_table.sortByColumn(top_fail_col, Qt.SortOrder.DescendingOrder)
        else:
            test_id_col = self.cpk_info_table.get_column_index(GlobalVariable.TEST_ID_COLUMN_NAME)
            self.cpk_info_table.sortByColumn(test_id_col, Qt.SortOrder.AscendingOrder)

    @Slot()
    def on_pushButton_pressed(self):
        """
        第一步：改变Limit后重算Rate
        基于原始数据和新的limit重新计算fail rate，不修改原始数据
        """
        new_limit = QTableUtils.get_all_new_limit(self.cpk_info_table)
        if not new_limit:
            self.li.QStatusMessage.emit("请先在表格中修改limit值!")
            return

        # 显示将要使用的新limit值
        limit_info = []
        for test_id, (lo_limit, hi_limit, _, _) in new_limit.items():
            limit_info.append(f"TEST_ID {test_id}: [{lo_limit}, {hi_limit}]")

        limit_text = "\n".join(limit_info[:5])  # 最多显示5个
        if len(limit_info) > 5:
            limit_text += f"\n... 还有{len(limit_info)-5}个测试项目"

        if self.message_show(f"将使用以下新的limit重新计算fail rate:\n{limit_text}\n\n确认继续吗？"):
            success = self.li.update_limit(new_limit, False)
            if success:
                # 刷新表格显示新的计算结果
                self.cal_table()
                # 启用后续操作按钮
                self.pushButton_2.setEnabled(True)
                self.pushButton_4.setEnabled(True)

    @Slot()
    def on_pushButton_2_pressed(self):
        """
        第二步：还原到原始Limit
        针对新修改的limit进行还原，让用户可以重新修改limit
        """
        # 检查是否已执行第一步
        if self.li._operation_state not in ['limit_changed', 'limit_restored']:
            self.li.QStatusMessage.emit("请先执行'改变Limit后重算Rate'操作!")
            return

        # 显示当前的limit变更信息
        if self.li._current_limit_changes:
            limit_info = []
            for test_id, (lo_limit, hi_limit, _, _) in self.li._current_limit_changes.items():
                limit_info.append(f"TEST_ID {test_id}: [{lo_limit}, {hi_limit}]")

            limit_text = "\n".join(limit_info[:5])  # 最多显示5个
            if len(limit_info) > 5:
                limit_text += f"\n... 还有{len(limit_info)-5}个测试项目"

            message = f"当前已修改的limit:\n{limit_text}\n\n确认还原到原始limit吗？\n还原后可以重新修改limit进行计算。"
        else:
            message = "确认还原到原始limit吗？\n还原后可以重新修改limit进行计算。"

        if self.message_show(message):
            success = self.li.restore_original_limits()
            if success:
                # 刷新表格显示
                self.cal_table()
                # 重新启用第一步按钮，禁用后续按钮
                self.pushButton.setEnabled(True)
                self.pushButton_2.setEnabled(False)
                self.pushButton_4.setEnabled(False)
                self.li.QStatusMessage.emit("已还原到原始limit，可以重新修改limit进行计算!")

    @Slot()
    def on_pushButton_4_pressed(self):
        """
        第三步：只对选中项目的数据进行分析
        基于前面操作的结果，进一步筛选分析范围
        """
        test_ids = QTableUtils.get_table_widget_test_id(self.cpk_info_table)
        if not test_ids:
            self.li.QStatusMessage.emit("请先选择要分析的测试项目!")
            return

        # 显示操作信息
        operation_info = "将只对选中的测试项目进行分析"
        if self.li._operation_state == 'limit_changed':
            operation_info += "\n（基于第一步的limit变更结果）"
        elif self.li._operation_state == 'data_filtered':
            operation_info += "\n（基于前面的数据过滤结果）"

        if self.message_show(f"{operation_info}\n\n选中的测试项目数量: {len(test_ids)}\n确认继续吗？"):
            self.li.screen_df(test_ids)
            # 刷新表格显示
            self.cal_table()
            self.li.QStatusMessage.emit(f"分析范围已限制为{len(test_ids)}个测试项目")

    def cpk_table_row_hide(self, hide: bool):
        for i in range(self.cpk_info_table.rowCount()):
            self.cpk_info_table.setRowHidden(i, hide)

    @Slot()
    def on_lineEdit_returnPressed(self):
        """
        若可以查询到, 先隐藏所有行
        """
        regex = self.lineEdit.text()
        regex = "*{}*".format(regex)
        items = self.cpk_info_table.findItems(regex, Qt.MatchWildcard)
        if len(items) == 0:
            self.li.QStatusMessage.emit("无法根据筛选条件查询到匹配行@!显示所有行.")
            self.cpk_table_row_hide(False)
            return
        self.cpk_table_row_hide(True)
        # 动态获取列索引
        test_num_col = self.cpk_info_table.get_column_index(GlobalVariable.TEST_NUM_COLUMN_NAME)
        test_txt_col = self.cpk_info_table.get_column_index(GlobalVariable.TEST_TXT_COLUMN_NAME)
        
        for each in items:
            if each.column() not in {test_num_col, test_txt_col}:
                continue
            self.cpk_info_table.setRowHidden(each.row(), False)

    def message_show(self, text: str) -> bool:
        res = QMessageBox.question(self, '待确认', text,
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.Yes)
        if res == QMessageBox.Yes:
            return True
        else:
            return False

    def message_show_with_options(self, title: str, option1: str, option2: str) -> int:
        """
        显示带有三个选项的对话框
        :param title: 对话框标题
        :param option1: 选项1文本
        :param option2: 选项2文本
        :return: 0=取消, 1=选项1, 2=选项2
        """
        msg = QMessageBox(self)
        msg.setWindowTitle('选择操作')
        msg.setText(title)

        btn1 = msg.addButton(option1, QMessageBox.ActionRole)
        btn2 = msg.addButton(option2, QMessageBox.ActionRole)
        msg.addButton('取消', QMessageBox.RejectRole)

        msg.exec_()

        if msg.clickedButton() == btn1:
            return 1
        elif msg.clickedButton() == btn2:
            return 2
        else:
            return 0

    def clear_table_data(self):
        """
        清空表格数据
        """
        self.cpk_info_table.clear()
        self.plot.clear()
        self.enable_buttons(False)
        from ui_component.ui_common.my_text_browser import Print
        Print.info("已清空Data TEST NO&ITEM Analysis表格")

    def enable_buttons(self, enabled: bool):
        """
        启用或禁用功能按钮
        初始时只启用第一个按钮，后续按钮根据操作流程启用
        :param enabled: True=启用, False=禁用
        """
        self.pushButton.setEnabled(enabled)  # 第一步：改变Limit后重算Rate
        # 第二步和第三步按钮初始时禁用，需要在第一步完成后启用
        self.pushButton_2.setEnabled(False)  # 第二步：删除选中项目Limit外的数据
        self.pushButton_4.setEnabled(False)  # 第三步：只对选中项目的数据进行分析
