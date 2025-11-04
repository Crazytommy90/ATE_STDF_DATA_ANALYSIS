#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : ui_summary_widget.py
@Author  : Link
@Time    : 2025/10/30
@Mark    : Summary显示组件
"""
import os
from typing import List, Dict
from PySide2.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTextEdit
from PySide2.QtGui import QFont
from PySide2.QtCore import Qt

from common.li import Li, SummaryCore
from common.app_variable import DataModule
from common.summary_generator import SummaryGenerator
from common.stdf_interface.stdf_parser import SemiStdfUtils
from parser_core.stdf_parser_file_write_read import ParserData


class SummaryWidget(QWidget):
    """
    Summary显示组件
    使用Tab显示多个Summary：
    - 第一个Tab：综合Summary（所有数据）
    - 后续Tab：每个文件的独立Summary
    """
    
    def __init__(self, li: Li, summary: SummaryCore, parent=None):
        super(SummaryWidget, self).__init__(parent)
        self.li = li
        self.summary = summary
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建Tab控件
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        self.setLayout(layout)
    
    def generate_summaries(self):
        """
        生成Summary报告
        1. 综合Summary（所有数据）
        2. 每个文件的独立Summary
        """
        if self.li.df_module is None or self.li.select_summary is None:
            self.add_error_tab("错误", "请先加载STDF数据")
            return
        
        # 清空现有Tab
        self.tab_widget.clear()
        
        # 1. 生成综合Summary
        self.generate_combined_summary()
        
        # 2. 为每个文件生成独立Summary
        self.generate_individual_summaries()
    
    def generate_combined_summary(self):
        """生成综合Summary（所有数据）"""
        try:
            # 获取综合信息
            summary_df = self.li.select_summary
            
            if len(summary_df) == 0:
                self.add_error_tab("综合Summary", "没有可用的数据")
                return
            
            # 合并所有文件的基本信息
            combined_info = {
                'LOT_ID': ', '.join(summary_df['LOT_ID'].unique().astype(str)),
                'SBLOT_ID': ', '.join(summary_df['SBLOT_ID'].unique().astype(str)) if 'SBLOT_ID' in summary_df.columns else '',
                'WAFER_ID': ', '.join(summary_df['WAFER_ID'].unique().astype(str)) if 'WAFER_ID' in summary_df.columns else '',
                'TEST_COD': ', '.join(summary_df['TEST_COD'].unique().astype(str)) if 'TEST_COD' in summary_df.columns else '',
                'FLOW_ID': ', '.join(summary_df['FLOW_ID'].unique().astype(str)) if 'FLOW_ID' in summary_df.columns else '',
                'PART_TYP': ', '.join(summary_df['PART_TYP'].unique().astype(str)) if 'PART_TYP' in summary_df.columns else '',
                'JOB_NAM': ', '.join(summary_df['JOB_NAM'].unique().astype(str)) if 'JOB_NAM' in summary_df.columns else '',
                'NODE_NAM': ', '.join(summary_df['NODE_NAM'].unique().astype(str)) if 'NODE_NAM' in summary_df.columns else '',
                'TST_TEMP': summary_df['TST_TEMP'].iloc[0] if 'TST_TEMP' in summary_df.columns and len(summary_df) > 0 else 0,
                'SETUP_T': summary_df['SETUP_T'].min() if 'SETUP_T' in summary_df.columns else 0,
                'START_T': summary_df['START_T'].min() if 'START_T' in summary_df.columns else 0,
                'SITE_CNT': summary_df['SITE_CNT'].max() if 'SITE_CNT' in summary_df.columns else 0,
            }
            
            # 文件信息（综合Summary）- 优化：直接从summary_df读取静态信息
            file_info = {
                'FILE_PATH': f"Combined ({len(summary_df)} files)",
                'FILE_NAME': "Combined Summary",
                # 从summary_df读取静态信息（已在加载时提取，避免重复读取STDF文件）
                'FINISH_TIME': SummaryGenerator.format_timestamp(summary_df['FINISH_T'].max() if 'FINISH_T' in summary_df.columns else 0),
                'TESTER_TYPE': ', '.join(summary_df['NODE_NAM'].unique().astype(str)) if 'NODE_NAM' in summary_df.columns else '--------',
                'EXEC_TYPE': ', '.join(summary_df['EXEC_TYP'].unique().astype(str)) if 'EXEC_TYP' in summary_df.columns else '--------',
                'EXEC_VER': ', '.join(summary_df['EXEC_VER'].unique().astype(str)) if 'EXEC_VER' in summary_df.columns else '--------',
                'TEST_MODE': ', '.join(summary_df['MODE_COD'].unique().astype(str)) if 'MODE_COD' in summary_df.columns else '--------',
                'STAT_NUM': ', '.join(summary_df['STAT_NUM'].astype(str).unique()) if 'STAT_NUM' in summary_df.columns else '--------',
                'OPER_NAM': ', '.join(summary_df['OPER_NAM'].unique().astype(str)) if 'OPER_NAM' in summary_df.columns else '--------',
                'BURN_TIM': ', '.join(summary_df['BURN_TIM'].astype(str).unique()) if 'BURN_TIM' in summary_df.columns else '--------',
            }
            
            # 生成Summary文本
            summary_text = SummaryGenerator.generate_summary_text(
                combined_info,
                file_info,
                self.li.df_module
            )
            
            # 添加到Tab
            self.add_summary_tab("综合Summary", summary_text)
        
        except Exception as e:
            self.add_error_tab("综合Summary", f"生成综合Summary失败: {str(e)}")
    
    def generate_individual_summaries(self):
        """
        为每个文件生成独立Summary
        优化：
        1. 直接从summary_df读取静态信息，避免重复读取STDF文件
        2. 一次性分组prr_df，避免重复筛选
        """
        try:
            summary_df = self.li.select_summary

            # 优化：一次性按ID分组prr_df，避免重复筛选
            if self.li.df_module is None or self.li.df_module.prr_df is None:
                self.add_error_tab("独立Summary", "没有可用的PRR数据")
                return

            # 检查是否有ID列
            if 'ID' not in self.li.df_module.prr_df.columns:
                # 如果没有ID列，只能逐个筛选
                grouped_prr = None
                grouped_dtp = None
            else:
                # 一次性分组，避免重复筛选
                grouped_prr = self.li.df_module.prr_df.groupby('ID')
                grouped_dtp = self.li.df_module.dtp_df.groupby('ID') if self.li.df_module.dtp_df is not None and 'ID' in self.li.df_module.dtp_df.columns else None

            # 按ID遍历每个文件
            for idx, row in summary_df.iterrows():
                file_id = row.get('ID', idx)
                file_path = row.get('FILE_PATH', '')

                # 获取文件名
                file_name = os.path.basename(file_path) if file_path else f"File_{file_id}"

                # 从summary_df获取基本信息
                summary_info = {
                    'LOT_ID': row.get('LOT_ID', ''),
                    'SBLOT_ID': row.get('SBLOT_ID', ''),
                    'WAFER_ID': row.get('WAFER_ID', ''),
                    'TEST_COD': row.get('TEST_COD', ''),
                    'FLOW_ID': row.get('FLOW_ID', ''),
                    'PART_TYP': row.get('PART_TYP', ''),
                    'JOB_NAM': row.get('JOB_NAM', ''),
                    'NODE_NAM': row.get('NODE_NAM', ''),
                    'TST_TEMP': row.get('TST_TEMP', 0),
                    'SETUP_T': row.get('SETUP_T', 0),
                    'START_T': row.get('START_T', 0),
                    'SITE_CNT': row.get('SITE_CNT', 0),
                }

                # 优化：直接从summary_df读取静态信息（已在加载时提取）
                file_info = {
                    'FILE_PATH': file_path,
                    'FILE_NAME': file_name,
                    'FINISH_TIME': SummaryGenerator.format_timestamp(row.get('FINISH_T', 0)),
                    'TESTER_TYPE': row.get('NODE_NAM', '--------'),
                    'EXEC_TYPE': row.get('EXEC_TYP', '--------'),
                    'EXEC_VER': row.get('EXEC_VER', '--------'),
                    'TEST_MODE': row.get('MODE_COD', '--------'),
                    'STAT_NUM': str(row.get('STAT_NUM', '--------')),
                    'OPER_NAM': row.get('OPER_NAM', '--------'),
                    'BURN_TIM': str(row.get('BURN_TIM', '--------')),
                }

                # 优化：使用分组结果，避免重复筛选
                if grouped_prr is not None:
                    try:
                        file_prr_df = grouped_prr.get_group(file_id)
                        file_dtp_df = grouped_dtp.get_group(file_id) if grouped_dtp is not None else None
                        file_df_module = DataModule(
                            prr_df=file_prr_df,
                            dtp_df=file_dtp_df,
                            ptmd_df=None
                        )
                    except KeyError:
                        # 如果分组中没有该ID，使用传统筛选方式
                        file_df_module = self.filter_data_by_id(file_id)
                else:
                    # 没有ID列，使用传统筛选方式
                    file_df_module = self.filter_data_by_id(file_id)
                
                if file_df_module is None:
                    self.add_error_tab(file_name, f"无法加载文件 {file_name} 的数据")
                    continue
                
                # 生成Summary文本
                summary_text = SummaryGenerator.generate_summary_text(
                    summary_info,
                    file_info,
                    file_df_module
                )
                
                # 添加到Tab
                self.add_summary_tab(file_name, summary_text)
        
        except Exception as e:
            self.add_error_tab("错误", f"生成独立Summary失败: {str(e)}")
    
    def filter_data_by_id(self, file_id: int) -> DataModule:
        """
        根据文件ID筛选数据
        :param file_id: 文件ID
        :return: 筛选后的DataModule
        """
        try:
            if self.li.df_module is None:
                return None
            
            # 筛选PRR数据
            prr_df = self.li.df_module.prr_df
            if 'ID' in prr_df.columns:
                filtered_prr = prr_df[prr_df['ID'] == file_id].copy()
            else:
                filtered_prr = prr_df.copy()
            
            # 筛选DTP数据
            dtp_df = self.li.df_module.dtp_df
            if 'ID' in dtp_df.columns:
                filtered_dtp = dtp_df[dtp_df['ID'] == file_id].copy()
            else:
                filtered_dtp = dtp_df.copy()
            
            # 筛选PTMD数据（通常不需要按ID筛选）
            filtered_ptmd = self.li.df_module.ptmd_df.copy()
            
            return DataModule(
                prr_df=filtered_prr,
                dtp_df=filtered_dtp,
                ptmd_df=filtered_ptmd
            )
        
        except Exception as e:
            print(f"Error filtering data by ID {file_id}: {e}")
            return None
    
    def add_summary_tab(self, tab_name: str, summary_text: str):
        """
        添加Summary Tab
        :param tab_name: Tab名称
        :param summary_text: Summary文本内容
        """
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(summary_text)
        
        # 设置等宽字体以保持对齐
        font = QFont("Courier New", 9)
        text_edit.setFont(font)
        
        # 设置样式
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
            }
        """)
        
        self.tab_widget.addTab(text_edit, tab_name)
    
    def add_error_tab(self, tab_name: str, error_message: str):
        """
        添加错误信息Tab
        :param tab_name: Tab名称
        :param error_message: 错误信息
        """
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(f"错误: {error_message}")
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #fff5f5;
                color: #cc0000;
                border: 1px solid #ff0000;
            }
        """)
        
        self.tab_widget.addTab(text_edit, tab_name)

