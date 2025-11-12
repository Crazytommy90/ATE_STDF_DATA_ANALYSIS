"""
-*- coding: utf-8 -*-
@Author  : Link
@Time    : 2022/5/9 17:44
@Software: PyCharm
@File    : ui_tree_load_widget.py
@Remark  :
"""
from typing import List

from PySide2.QtCore import Slot, QThread, Signal
from PySide2.QtWidgets import QWidget, QTreeWidgetItem, QInputDialog

from common.li import SummaryCore, Li
from ui_component.ui_analysis_stdf.ui_designer.ui_tree_load import Ui_Form as TreeLoadForm
from ui_component.ui_common.my_text_browser import Print
from ui_component.ui_common.ui_utils import TreeUtils, QWidgetUtils


class QthCalculation(QThread):
    li = None
    summary = None
    ids = None
    eventSignal = Signal(int)

    def set_li(self, li: Li):
        self.li = li

    def set_summary(self, summary: SummaryCore):
        self.summary = summary

    def set_ids(self, ids: List[int]):
        self.ids = ids

    def event_send(self, i: int):
        self.eventSignal.emit(i)

    def run(self) -> None:
        self.event_send(1)
        self.li.set_data(*self.summary.load_select_data(
            self.ids, self.parent().checkBox.checkState(), self.parent().spinBox.value()
        ))
        self.event_send(2)
        self.li.concat()
        
        # 根据加载类型过滤数据
        if hasattr(self.parent(), '_load_type') and self.parent()._load_type:
            from common.app_variable import DatatType
            if self.parent()._load_type == 'P':
                self.li.filter_by_test_type([DatatType.PTR, DatatType.MPR])
            elif self.parent()._load_type == 'F':
                self.li.filter_by_test_type([DatatType.FTR])
            # 'PF' 或 None 不过滤，加载所有数据
        
        self.event_send(3)
        self.li.calculation_top_fail()
        self.event_send(4)
        self.li.calculation_capability()
        self.event_send(5)
        self.li.background_generation_data_use_to_chart_and_to_save_csv()
        self.event_send(6)


class TreeLoadWidget(QWidget, TreeLoadForm):
    """
    DataTree & Limit List
    """
    parent = None

    def __init__(self, li: Li, summary: SummaryCore, parent=None):
        super(TreeLoadWidget, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Data Tree Select & Config")
        self.li = li
        self.summary = summary
        self.th = QthCalculation(self)
        self.th.eventSignal.connect(lambda x: self.progressBar.setValue(x))
        self.th.set_li(self.li)
        self.th.set_summary(self.summary)
        self.th.finished.connect(self.li.update)
        self.progressBar.setMaximum(6)
        self.pushButton_2.setEnabled(True)
        
        # 添加P和F数据载入按钮
        from PySide2.QtWidgets import QPushButton
        self.btn_load_p = QPushButton("P数据载入")
        self.btn_load_p.clicked.connect(self.on_load_p_data)
        self.horizontalLayout.insertWidget(1, self.btn_load_p)
        
        self.btn_load_f = QPushButton("F数据载入")
        self.btn_load_f.clicked.connect(self.on_load_f_data)
        self.horizontalLayout.insertWidget(2, self.btn_load_f)
        
        # 添加清空按钮
        self.btn_clear_tree = QPushButton("清空")
        self.btn_clear_tree.clicked.connect(self.clear_tree_data)
        self.horizontalLayout.insertWidget(4, self.btn_clear_tree)
        
        # 用于标记当前加载类型
        self._load_type = None

    @Slot(QTreeWidgetItem)
    def on_treeWidget_itemChanged(self, e: QTreeWidgetItem):
        TreeUtils.tree_item_change(self.treeWidget, e)

    @Slot()
    def on_pushButton_pressed(self):
        """
        P&F数据载入 - 加载所有类型的测试数据
        """
        self._load_type = 'PF'
        self._execute_load()
    
    @Slot()
    def on_load_p_data(self):
        """
        P数据载入 - 仅加载Parametric类测试（PTR, MPR）
        """
        self._load_type = 'P'
        self._execute_load()
    
    @Slot()
    def on_load_f_data(self):
        """
        F数据载入 - 仅加载Functional类测试（FTR）
        """
        self._load_type = 'F'
        self._execute_load()
    
    def _execute_load(self):
        """
        执行数据加载的通用逻辑
        """
        if self.th.isRunning():
            return Print.warning("工作线程正在运行中!")
        if self.summary.summary_df is None:
            return Print.warning("未载入数据到数据空间!")
        self.th.set_summary(self.summary)
        self.th.set_li(self.li)
        ids = TreeUtils.get_tree_ids(self.treeWidget)
        if self.li is None:
            return Print.warning("未载入Li!")
        if not ids:
            return Print.warning("未选择数据!")
        self.progressBar.setValue(0)
        self.th.set_ids(ids)
        self.th.start()

    @Slot()
    def on_pushButton_2_pressed(self):
        """
        Merge多份数据成为一份自定义的数据
        """
        ids = TreeUtils.get_tree_ids(self.treeWidget)
        if not ids:
            return Print.warning("未载入数据到数据空间, 无法解析!")
        remark, _ = QInputDialog.getText(self, "输入自定义LOT_ID", "请填写自定义的LOT_ID用于整合多个LOT成为一个数据;自定义输入的长度不能<2!")
        remark = remark.replace(" ", "").upper()
        if len(remark) < 2:
            return Print.warning("自定义输入的长度不能<2!")
        self.summary.add_custom_node(ids, remark)
        TreeUtils.set_data_to_tree(self.treeWidget, self.summary.get_summary_tree(), True)
        self.treeWidget.expandAll()

    def clear_tree_data(self):
        """
        清空Tree中已载入的STDF数据显示
        """
        self.treeWidget.clear()
        self.progressBar.setValue(0)
        Print.info("已清空Data Tree显示")

    def set_tree(self):
        if not self.summary.ready:
            return Print.warning("数据解析未成功的!")
        TreeUtils.set_data_to_tree(self.treeWidget, self.summary.get_summary_tree(), True)
        self.treeWidget.expandAll()
        QWidgetUtils.widget_change_color(widget=self, background_color="#3316C6")
