#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : table_module.py
@Author  : Link
@Time    : 2022/5/1 21:39
@Mark    : 
"""
from typing import Union, List, Set, Dict

from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Qt
from PySide2.QtGui import QFont
from PySide2.QtWidgets import QTableWidgetItem, QTableWidget, QComboBox, QStyledItemDelegate
from pyqtgraph import TableWidget

from common.app_variable import GlobalVariable
from common.func import timestamp_to_str

translate = QtCore.QCoreApplication.translate


class PauseTableWidget(TableWidget):

    def __init__(self, *args, **kwds):
        super(PauseTableWidget, self).__init__(*args, **kwds)

        self.contextMenu.addAction(translate("PauseTableWidget", 'Paste')).triggered.connect(self.paste)

    q_font = QFont("", 8)

    def setData(self, data):
        self.setAlternatingRowColors(True)
        self.q_font.setBold(True)
        self.horizontalHeader().setFont(self.q_font)
        self.setFont(self.q_font)

        # 预处理数据，确保limit值和其他浮点数显示正确的精度
        # 由于pyqtgraph TableWidget的格式设置不起作用，我们手动格式化数据
        if data:
            formatted_data = []

            # 需要格式化的浮点数字段
            float_fields = {
                'LO_LIMIT': 9,       # LO_LIMIT显示9位小数，支持uA级别
                'HI_LIMIT': 9,       # HI_LIMIT显示9位小数，支持uA级别
                'AVG': 9,            # 平均值显示9位小数
                'STD': 9,            # 标准差显示9位小数
                'CPK': 6,            # CPK显示6位小数（通常不需要太高精度）
                'MIN': 9,            # 最小值显示9位小数
                'MAX': 9,            # 最大值显示9位小数
                'ALL_DATA_MIN': 9,   # 全数据最小值显示9位小数
                'ALL_DATA_MAX': 9,   # 全数据最大值显示9位小数
            }

            def smart_format_float(value, precision=9, min_decimals=3):
                """
                智能格式化浮点数：
                - 对于绝对值 >= 1e-3 的数值，使用固定小数点格式
                - 对于绝对值 < 1e-3 的数值，使用科学记数法
                - 对于零值，显示为 "0"
                - 智能检测有效数字，移除浮点数精度误差导致的尾数
                """
                if value == 0:
                    return "0"

                abs_value = abs(value)

                # 对于非常小的数值（< 1e-3）或非常大的数值（>= 1e6），使用科学记数法
                if (abs_value < 1e-3 and abs_value != 0) or abs_value >= 1e6:
                    # 智能检测科学记数法的精度
                    # 策略：尝试不同的精度，找到最简洁但准确的表示

                    # 对于科学记数法，从1位小数开始测试
                    for test_decimals in range(1, precision + 1):
                        # 格式化为科学记数法
                        formatted = f"{value:.{test_decimals}e}"

                        # 解析科学记数法字符串，提取尾数和指数
                        # 例如: "1.400000037e-04" -> mantissa=1.400000037, exponent=-04
                        parts = formatted.lower().split('e')
                        if len(parts) == 2:
                            mantissa_str = parts[0]
                            exponent_str = parts[1]

                            # 将字符串转回浮点数进行比较
                            reconstructed_value = float(formatted)

                            # 检查相对误差
                            if abs_value > 0:
                                relative_error = abs(reconstructed_value - value) / abs_value
                                if relative_error < 0.001:  # 0.1%的相对误差
                                    # 找到合适的精度，移除尾随零
                                    if '.' in mantissa_str:
                                        mantissa_parts = mantissa_str.split('.')
                                        integer_part = mantissa_parts[0]
                                        decimal_part = mantissa_parts[1].rstrip('0')

                                        # 至少保留1位小数
                                        if not decimal_part:
                                            decimal_part = '0'

                                        mantissa_str = f"{integer_part}.{decimal_part}"

                                    return f"{mantissa_str}e{exponent_str}"

                    # 如果没有找到合适的精度，使用默认精度并移除尾随零
                    formatted = f"{value:.{precision}e}"
                    parts = formatted.lower().split('e')
                    if len(parts) == 2:
                        mantissa_str = parts[0]
                        exponent_str = parts[1]
                        if '.' in mantissa_str:
                            mantissa_parts = mantissa_str.split('.')
                            integer_part = mantissa_parts[0]
                            decimal_part = mantissa_parts[1].rstrip('0')
                            if not decimal_part:
                                decimal_part = '0'
                            mantissa_str = f"{integer_part}.{decimal_part}"
                        return f"{mantissa_str}e{exponent_str}"

                    return formatted

                # 对于正常范围的数值，使用固定小数点格式
                else:
                    # 策略：尝试不同的精度，找到最简洁但准确的表示
                    # 从min_decimals开始，逐步增加精度，直到找到合适的表示

                    for test_decimals in range(min_decimals, precision + 1):
                        rounded_value = round(value, test_decimals)
                        # 检查四舍五入后的值是否与原值足够接近
                        # 使用相对误差 < 0.1% 作为判断标准
                        if abs_value > 0:
                            relative_error = abs(rounded_value - value) / abs_value
                            if relative_error < 0.001:  # 0.1%的相对误差
                                # 找到合适的精度，格式化并移除尾随零
                                formatted = f"{rounded_value:.{test_decimals}f}"
                                # 移除尾随零，但保留至少min_decimals位小数
                                if '.' in formatted:
                                    integer_part, decimal_part = formatted.split('.')
                                    decimal_part_stripped = decimal_part.rstrip('0')
                                    if len(decimal_part_stripped) < min_decimals:
                                        decimal_part_stripped = decimal_part[:min_decimals]
                                    if not decimal_part_stripped:
                                        decimal_part_stripped = '0' * min_decimals
                                    formatted = f"{integer_part}.{decimal_part_stripped}"
                                return formatted

                    # 如果没有找到合适的精度，使用最大精度
                    formatted = f"{value:.{precision}f}"
                    if '.' in formatted:
                        integer_part, decimal_part = formatted.split('.')
                        decimal_part_stripped = decimal_part.rstrip('0')
                        if len(decimal_part_stripped) < min_decimals:
                            decimal_part_stripped = decimal_part[:min_decimals]
                        if not decimal_part_stripped:
                            decimal_part_stripped = '0' * min_decimals
                        formatted = f"{integer_part}.{decimal_part_stripped}"
                    return formatted

            for item in data:
                formatted_item = {}
                for key, value in item.items():
                    if key in float_fields and isinstance(value, (int, float)):
                        # 使用智能格式化
                        precision = float_fields[key]
                        # 对于limit字段，至少保留3位小数；其他字段保留1位小数
                        min_decimals = 3 if key in ['LO_LIMIT', 'HI_LIMIT'] else 1
                        formatted_item[key] = smart_format_float(value, precision, min_decimals)
                    else:
                        # 保持原始值
                        formatted_item[key] = value
                formatted_data.append(formatted_item)

            # 使用格式化后的数据
            super(PauseTableWidget, self).setData(formatted_data)
        else:
            # 如果没有数据，直接调用父类方法
            super(PauseTableWidget, self).setData(data)

    def get_column_index(self, column_name: str) -> int:
        """
        根据列名获取列索引
        :param column_name: 列名
        :return: 列索引，如果找不到返回-1
        """
        for col in range(self.columnCount()):
            header_item = self.horizontalHeaderItem(col)
            if header_item and header_item.text() == column_name:
                return col
        return -1

    def get_select_row_set(self, column: int) -> Union[None, set]:
        selection = self.selectedRanges()
        if not selection:
            return None

    def paste(self):
        """
        将剪切板的数据复制到TableWidget中
        先找到选中的行列位置
        再根据数据来进行黏贴
        """
        text = QtWidgets.QApplication.clipboard().text()  # type:str
        split_text_rows = text.split('\n')
        if len(split_text_rows) == 0:
            return
        text_rows = split_text_rows[1:-1]
        selection = self.selectedRanges()
        if not selection:
            return
        selection = selection[0]
        select_row = selection.topRow()
        select_column = selection.leftColumn()

        pause_row = len(text_rows)
        for i in range(pause_row):
            item_row = i + select_row
            row_split_text = text_rows[i].split('\t')
            for j in range(len(row_split_text)):
                item_column = select_column + j
                item = self.item(item_row, item_column)  # type:QtWidgets.QTableWidgetItem
                if item is None:
                    continue
                item.setText(row_split_text[j])

    def keyPressEvent(self, ev):
        if ev.matches(QtGui.QKeySequence.StandardKey.Paste):
            ev.accept()
            self.paste()
        else:
            super().keyPressEvent(ev)


class SearchTableWidget(TableWidget):
    """
    用在需要选取在哪行的table上, 从数据库中获取id, id都是小写
    """
    temp_data = None  # type:List[dict]
    cache_index = None  # type:dict
    q_font = QFont("", 8)

    def setData(self, data):
        self.horizontalHeader().setFont(self.q_font)
        self.setFont(self.q_font)
        self.cache_index = {}
        self.temp_data = data
        self._sorting = False
        super(SearchTableWidget, self).setData(data)
        self.set_cache_index()

    def set_cache_index(self):
        if self.temp_data is None:
            return
        for index, each in enumerate(self.temp_data):
            id_cache = self.cache_index.get(each["METHOD"], None)
            if id_cache is None:
                id_cache = {}
                self.cache_index[each["METHOD"]] = id_cache
            id_cache[each["ID"]] = index

    def get_table_select(self) -> Union[List[dict], None]:
        """
        需要第一列是id
        """
        items = self.selectedItems()
        select_index = set([
            self.row(each) for each in items
        ])
        if not select_index:
            return None
        data = []
        for index in select_index:
            method = self.item(index, 1).text()
            sql_id = int(self.item(index, 0).text())
            index = self.cache_index[method][sql_id]
            data.append(self.temp_data[index])
        return data

    def get_ids(self):
        items = self.selectedItems()
        select_index = set([
            self.row(each) for each in items
        ])
        ids = []
        if not select_index:
            return ids
        for each in select_index:
            ids.append(int(self.item(each, 0).text()))
        return ids


class BaseTableWidget(QTableWidget):
    table_count = 0
    table_head_index = None
    table_head = None
    temp_table_data = None
    q_font = QFont("", 8)

    def clear(self) -> None:
        self.temp_table_data = None
        self.table_count = 0
        super(BaseTableWidget, self).clear()

    def clearContents(self) -> None:
        self.temp_table_data = None
        self.table_count = 0
        super(BaseTableWidget, self).clearContents()

    def set_table_head(self, table_head: List[str]):
        """

        :param table_head:
        :return:
        """
        self.table_head = table_head
        self.table_head_index = {}
        for index, each in enumerate(self.table_head):
            self.table_head_index[each] = index
        self.setColumnCount(len(table_head))
        self.setHorizontalHeaderLabels(table_head)
        self.horizontalHeader().setFont(self.q_font)

    def update_table_data(self, index: int, column: str, item: QTableWidgetItem) -> bool:
        if index >= self.table_count:
            return False
        self.setItem(index, self.table_head_index[column], item)
        return True

    def paste(self):
        text = QtWidgets.QApplication.clipboard().text()  # type:str
        split_text_rows = text.split('\n')
        if len(split_text_rows) == 0:
            return
        text_rows = split_text_rows[1:-1]
        selection = self.selectedRanges()
        if not selection:
            return
        selection = selection[0]
        select_row = selection.topRow()
        select_column = selection.leftColumn()

        pause_row = len(text_rows)
        for i in range(pause_row):
            item_row = i + select_row
            row_split_text = text_rows[i].split('\t')
            for j in range(len(row_split_text)):
                item_column = select_column + j
                item = self.item(item_row, item_column)  # type:QtWidgets.QTableWidgetItem
                if item is None:
                    continue
                item.setText(row_split_text[j])

    def keyPressEvent(self, ev):
        if ev.matches(QtGui.QKeySequence.StandardKey.Paste):
            ev.accept()
            self.paste()
        else:
            super().keyPressEvent(ev)


class ReadOnlyItemDelegate(QStyledItemDelegate):
    """
    委托, 让TableWidget内的Item无法被编辑
    """

    def createEditor(self, parent, option, index):
        return None


class QtTableWidget(BaseTableWidget):
    """
    用在需要读取复测数据的table上, 只能用专用的class
    ReadR 和 PartFlg
    """

    def set_table_data(self, table_data: List[dict]) -> bool:
        """
        第一列设置checkbox, 列名为是否为最后复测，勾选后只会选取这个数据的Fail Result
        TODO: 第二列设置为 PART_TYPE
        第三列设置message, 用来提示使用人员STDF处理进程
        后面列则为MIR相关数据

        :param table_data:
        :return:
        """
        if len(table_data) == 0:
            return False
        self.temp_table_data = table_data
        self.table_count = len(table_data)
        self.setRowCount(self.table_count)
        for row, each_row in enumerate(table_data):

            check_item = QTableWidgetItem()
            check_item.setCheckState(Qt.Unchecked)
            check_item.setText("R_FAIL")
            self.setItem(row, 0, check_item)

            combobox_column = QComboBox()
            combobox_column.addItems(GlobalVariable.PART_FLAGS)
            self.setCellWidget(row, 1, combobox_column)

            for key, item in each_row.items():
                if key in GlobalVariable.SKIP_FILE_TABLE_DATA_HEAD:
                    continue
                if key not in self.table_head_index:
                    continue
                column = self.table_head_index[key]
                if isinstance(item, QTableWidgetItem):
                    self.setItem(row, column, item)
                else:
                    if key[-2:] == "_T":
                        item = QTableWidgetItem(timestamp_to_str(item))
                    else:
                        item = QTableWidgetItem(str(item))
                    self.setItem(row, column, item)
        """
        重置 progressBar
        """
        # self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.resizeColumnsToContents()
        self.setFont(self.q_font)
        self.resizeRowsToContents()
        return True

    def get_part_flag(self) -> Dict[int, int]:
        li = dict()
        for row in range(self.table_count):
            combobox = self.cellWidget(row, 1)  # type:QComboBox
            li[row] = combobox.currentIndex()
        return li

    def set_all_part_flag(self, flag: int):
        for row in range(self.table_count):
            combobox = self.cellWidget(row, 1)  # type:QComboBox
            combobox.setCurrentIndex(flag)

    def update_temp_part_data(self):
        if self.temp_table_data is None:
            return
        flag_dict = self.get_part_flag()
        for index, each in enumerate(self.temp_table_data):
            each["PART_FLAG"] = flag_dict[index]

    def get_retest_row(self) -> Set[int]:
        """
        获取选取重测数据的下标
        :return:
        """
        li = set()
        for row in range(self.table_count):
            if self.item(row, 0).checkState() == Qt.Checked:
                li.add(row)
        return li

    def update_temp_r_data(self):
        if self.temp_table_data is None:
            return
        r_set = self.get_retest_row()
        for index, each in enumerate(self.temp_table_data):
            if index in r_set:
                each["READ_FAIL"] = True
            else:
                each["READ_FAIL"] = False

    def set_read_all_r(self, status):
        for row in range(self.table_count):
            self.item(row, 0).setCheckState(status)

    def update_temp_data(self):
        self.update_temp_part_data()
        self.update_temp_r_data()
