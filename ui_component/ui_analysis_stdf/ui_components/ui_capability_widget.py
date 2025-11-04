#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : ui_capability_widget.py
@Author  : Link
@Time    : 2025/10/30
@Mark    : 制程能力报告显示组件（混合显示：Table + 统计摘要）
"""
import os
from typing import List, Dict
import pandas as pd
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                                QTableWidget, QTableWidgetItem, QPushButton,
                                QTextEdit, QSplitter, QHeaderView, QMessageBox,
                                QFileDialog, QAbstractItemView)
from PySide2.QtGui import QFont, QColor
from PySide2.QtCore import Qt

from common.li import Li
from common.app_variable import DataModule
from common.capability_report_generator import CapabilityReportGenerator


class CapabilityWidget(QWidget):
    """
    制程能力报告显示组件
    混合显示：Table（可排序） + 统计摘要（文本）
    """
    
    def __init__(self, li: Li, parent=None):
        super().__init__(parent)
        self.li = li
        self.parent_widget = parent
        
        self.init_ui()
        self.generate_reports()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 创建Tab Widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建按钮栏
        button_layout = QHBoxLayout()
        
        self.btn_copy = QPushButton("复制当前表格")
        self.btn_copy.clicked.connect(self.copy_current_table)
        button_layout.addWidget(self.btn_copy)
        
        self.btn_export_excel = QPushButton("导出为Excel")
        self.btn_export_excel.clicked.connect(self.export_to_excel)
        button_layout.addWidget(self.btn_export_excel)
        
        self.btn_refresh = QPushButton("刷新报告")
        self.btn_refresh.clicked.connect(self.generate_reports)
        button_layout.addWidget(self.btn_refresh)

        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def generate_reports(self):
        """生成所有报告"""
        try:
            # 清空现有Tab
            self.tab_widget.clear()
            
            # 1. 生成综合报告
            self.generate_combined_report()
            
            # 2. 生成单文件报告
            self.generate_individual_reports()
            
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "错误", f"生成报告失败: {str(e)}\n{traceback.format_exc()}")
    
    def generate_combined_report(self):
        """生成综合报告（所有数据）"""
        try:
            if self.li.capability_key_list is None or len(self.li.capability_key_list) == 0:
                self.add_error_tab("综合报告", "没有可用的制程能力数据")
                return
            
            # 筛选有效的测项
            valid_items = CapabilityReportGenerator.filter_valid_items(self.li.capability_key_list)
            
            if len(valid_items) == 0:
                self.add_error_tab("综合报告", "没有可评估CPK的测项（需要有limit）")
                return
            
            # 按CPK排序
            sorted_items = CapabilityReportGenerator.sort_by_cpk(valid_items, ascending=True)
            
            # 生成统计摘要
            stats = CapabilityReportGenerator.generate_summary_statistics(sorted_items)
            
            # 创建DataFrame
            df = CapabilityReportGenerator.create_dataframe(sorted_items)
            
            # 添加到Tab
            self.add_report_tab("综合报告", df, stats, sorted_items)
            
        except Exception as e:
            import traceback
            self.add_error_tab("综合报告", f"生成综合报告失败: {str(e)}\n{traceback.format_exc()}")
    
    def generate_individual_reports(self):
        """生成单文件报告"""
        try:
            if self.li.select_summary is None or len(self.li.select_summary) == 0:
                return
            
            summary_df = self.li.select_summary
            
            # 检查是否有ID列
            if 'ID' not in self.li.df_module.prr_df.columns:
                return
            
            # 按ID遍历每个文件
            for idx, row in summary_df.iterrows():
                file_id = row.get('ID', idx)
                file_name = os.path.basename(row.get('FILE_PATH', f"File_{file_id}"))
                
                # 筛选该文件的capability数据
                file_capability_list = [
                    item for item in self.li.capability_key_list
                    if item.get('TEST_ID') in self.li.df_module.ptmd_df.index
                ]
                
                # 筛选有效的测项
                valid_items = CapabilityReportGenerator.filter_valid_items(file_capability_list)
                
                if len(valid_items) == 0:
                    continue
                
                # 按CPK排序
                sorted_items = CapabilityReportGenerator.sort_by_cpk(valid_items, ascending=True)
                
                # 生成统计摘要
                stats = CapabilityReportGenerator.generate_summary_statistics(sorted_items)
                
                # 创建DataFrame
                df = CapabilityReportGenerator.create_dataframe(sorted_items)
                
                # 添加到Tab
                self.add_report_tab(file_name, df, stats, sorted_items)
                
        except Exception as e:
            import traceback
            print(f"生成单文件报告失败: {str(e)}\n{traceback.format_exc()}")
    
    def add_report_tab(self, tab_name: str, df: pd.DataFrame, stats: Dict, capability_list: List[dict]):
        """
        添加报告Tab（混合显示：统计摘要 + Table）
        
        :param tab_name: Tab名称
        :param df: DataFrame数据
        :param stats: 统计摘要
        :param capability_list: 原始capability数据（用于图表）
        """
        # 创建Splitter（上下分割）
        splitter = QSplitter(Qt.Vertical)
        
        # 1. 上部：统计摘要（文本）
        summary_text = CapabilityReportGenerator.format_summary_text(stats)
        text_edit = QTextEdit()
        text_edit.setPlainText(summary_text)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Courier New", 10))
        text_edit.setMaximumHeight(250)
        splitter.addWidget(text_edit)
        
        # 2. 下部：Table（可排序）
        table = self.create_table_from_dataframe(df)
        splitter.addWidget(table)
        
        # 设置分割比例
        splitter.setSizes([200, 600])
        
        # 添加到Tab
        self.tab_widget.addTab(splitter, tab_name)
        
        # 保存数据用于导出
        tab_index = self.tab_widget.count() - 1
        self.tab_widget.setTabToolTip(tab_index, f"测项数量: {len(df)}")
    
    def create_table_from_dataframe(self, df: pd.DataFrame) -> QTableWidget:
        """
        从DataFrame创建QTableWidget
        
        :param df: DataFrame
        :return: QTableWidget
        """
        table = QTableWidget()
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns.tolist())
        
        # 填充数据
        for row_idx, row in df.iterrows():
            for col_idx, col_name in enumerate(df.columns):
                value = row[col_name]
                
                # 格式化显示
                if pd.isna(value):
                    display_value = "N/A"
                elif isinstance(value, (int, float)):
                    if col_name in ['Cpk', 'Cp', 'Ppk', 'Pp']:
                        display_value = f"{value:.3f}"
                    elif col_name in ['Sigma']:
                        display_value = f"{value:.2f}"
                    elif col_name in ['平均值', '标准差', '中位数', '最小值', '最大值', '下限', '上限']:
                        display_value = f"{value:.6f}"
                    else:
                        display_value = str(value)
                else:
                    display_value = str(value)
                
                item = QTableWidgetItem(display_value)
                item.setTextAlignment(Qt.AlignCenter)
                
                # CPK颜色标记
                if col_name == 'Cpk' and not pd.isna(value):
                    if value < 1.0:
                        item.setBackground(QColor(255, 200, 200))  # 红色
                    elif value < 1.33:
                        item.setBackground(QColor(255, 255, 200))  # 黄色
                    else:
                        item.setBackground(QColor(200, 255, 200))  # 绿色
                
                table.setItem(row_idx, col_idx, item)
        
        # 设置表格属性
        table.setSortingEnabled(True)  # 允许排序
        table.setSelectionBehavior(QAbstractItemView.SelectRows)  # 选择整行
        table.setAlternatingRowColors(True)  # 交替行颜色
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        
        return table
    
    def add_error_tab(self, tab_name: str, error_message: str):
        """添加错误信息Tab"""
        text_edit = QTextEdit()
        text_edit.setPlainText(error_message)
        text_edit.setReadOnly(True)
        self.tab_widget.addTab(text_edit, tab_name)
    
    def copy_current_table(self):
        """复制当前Tab的表格数据到剪贴板"""
        try:
            current_widget = self.tab_widget.currentWidget()
            if current_widget is None:
                return
            
            # 查找Splitter中的Table
            if isinstance(current_widget, QSplitter):
                table = current_widget.widget(1)  # 下部是Table
                if isinstance(table, QTableWidget):
                    self.copy_table_to_clipboard(table)
                    QMessageBox.information(self, "成功", "表格数据已复制到剪贴板")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"复制失败: {str(e)}")
    
    def copy_table_to_clipboard(self, table: QTableWidget):
        """复制Table到剪贴板"""
        from PySide2.QtWidgets import QApplication
        
        # 获取表头
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        text = "\t".join(headers) + "\n"
        
        # 获取数据
        for row in range(table.rowCount()):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                row_data.append(item.text() if item else "")
            text += "\t".join(row_data) + "\n"
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def export_to_excel(self):
        """导出所有报告到Excel"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出Excel", "", "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # 创建Excel Writer
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 导出每个Tab
                for i in range(self.tab_widget.count()):
                    tab_name = self.tab_widget.tabText(i)
                    widget = self.tab_widget.widget(i)
                    
                    if isinstance(widget, QSplitter):
                        table = widget.widget(1)
                        if isinstance(table, QTableWidget):
                            df = self.table_to_dataframe(table)
                            # Excel sheet名称限制31个字符
                            sheet_name = tab_name[:31]
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            QMessageBox.information(self, "成功", f"报告已导出到: {file_path}")
            
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}\n{traceback.format_exc()}")
    
    def table_to_dataframe(self, table: QTableWidget) -> pd.DataFrame:
        """将QTableWidget转换为DataFrame"""
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        data = []

        for row in range(table.rowCount()):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        return pd.DataFrame(data, columns=headers)