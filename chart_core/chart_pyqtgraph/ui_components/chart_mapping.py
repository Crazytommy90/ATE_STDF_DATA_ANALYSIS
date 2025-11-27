#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : chart_mapping.py
@Author  : Link
@Time    : 2025/01/10 19:45
@Mark    : Mapping图表组件
"""

import math
import random
import numpy as np
import pandas as pd
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QSplitter)
from PySide2.QtCore import Slot, Qt
from PySide2.QtGui import QFont, QColor
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget, ImageItem, ColorBarItem
from pyqtgraph.Qt import QtWidgets

from chart_core.chart_pyqtgraph.ui_components.ui_unit_chart import UnitChartWindow
from common.li import Li
from ui_component.ui_app_variable import UiGlobalVariable


def coord_to_np(x, y, d, c):
    """将坐标数据转换为numpy数组"""
    valid_mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(d))

    if np.any(valid_mask):
        valid_x = x[valid_mask].astype(int)
        valid_y = y[valid_mask].astype(int)
        valid_d = d[valid_mask]

        # 确保坐标在有效范围内
        valid_x = np.clip(valid_x, 0, c.shape[0] - 1)
        valid_y = np.clip(valid_y, 0, c.shape[1] - 1)

        c[valid_x, valid_y] = valid_d


def create_dynamic_colormap(bin_values, fail_flags, mapping_type="SOFT_BIN"):
    """动态创建PASS/FAIL颜色映射"""
    unique_bins = {}
    bin_fail_counts = {}
    
    for bin_val, fail_flag in zip(bin_values, fail_flags):
        if not np.isnan(bin_val) and not np.isnan(fail_flag):
            bin_val_int = int(bin_val)
            fail_flag_int = int(fail_flag)
            
            if bin_val_int not in bin_fail_counts:
                bin_fail_counts[bin_val_int] = {0: 0, 1: 0}
            
            if fail_flag_int in [0, 1]:
                bin_fail_counts[bin_val_int][fail_flag_int] += 1
    
    for bin_val_int, counts in bin_fail_counts.items():
        unique_bins[bin_val_int] = 1 if counts[1] >= counts[0] else 0
    
    if not unique_bins:
        lut = np.array([[0, 0, 0, 255]], dtype=np.ubyte)
        return lut, {}
    
    pass_colors = [
        (100, 255, 100, 255), (50, 200, 50, 255),
        (0, 180, 0, 255), (0, 150, 0, 255),
    ]
    
    softbin_fail_colors = [
        (255, 100, 100, 255), (255, 150, 100, 255), (255, 200, 100, 255),
        (255, 255, 100, 255), (255, 200, 50, 255), (100, 200, 255, 255),
        (100, 100, 255, 255), (150, 100, 255, 255), (200, 100, 255, 255),
        (255, 100, 255, 255), (255, 100, 200, 255), (255, 100, 150, 255),
        (200, 100, 100, 255), (200, 150, 100, 255), (200, 200, 100, 255),
        (180, 180, 50, 255), (100, 150, 255, 255), (150, 100, 200, 255),
        (200, 100, 150, 255), (150, 150, 255, 255),
    ]
    
    hardbin_fail_colors = [
        (255, 100, 100, 255), (255, 150, 100, 255), (255, 200, 100, 255),
        (200, 100, 200, 255), (100, 100, 255, 255), (255, 255, 100, 255),
        (255, 100, 200, 255), (100, 200, 255, 255), (200, 150, 100, 255),
        (150, 100, 200, 255),
    ]
    
    fail_color_pool = softbin_fail_colors if mapping_type == "SOFT_BIN" else hardbin_fail_colors
    
    color_dict = {}
    pass_idx = 0
    fail_idx = 0
    
    sorted_bins = sorted(unique_bins.items(), key=lambda x: x[0])
    
    for bin_val, fail_flag in sorted_bins:
        if fail_flag == 1:
            color_dict[bin_val] = pass_colors[pass_idx % len(pass_colors)]
            pass_idx += 1
        else:
            color_dict[bin_val] = fail_color_pool[fail_idx % len(fail_color_pool)]
            fail_idx += 1
    
    max_bin = max(unique_bins.keys())
    lut_size = max_bin + 1
    lut = np.zeros((lut_size, 4), dtype=np.ubyte)
    lut[:, 3] = 255
    
    for bin_val, color in color_dict.items():
        if bin_val < lut_size:
            lut[bin_val] = color
    
    return lut, color_dict


class BinLegendWidget(QWidget):
    """Bin图例平铺显示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        # 标题
        title_label = QLabel("Bin Legend")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        self.layout.addWidget(title_label)
        
        # 图例容器（使用垂直布局支持多行）
        self.legend_container = QWidget()
        self.grid_layout = QVBoxLayout(self.legend_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(5)
        self.layout.addWidget(self.legend_container)
        self.layout.addStretch()
        
    def update_legend(self, stats_data, color_dict):
        """
        更新图例，支持单个或分组的统计数据
        
        参数:
            stats_data: 单个统计字典或分组的统计字典 {'group': stats}
            color_dict: {bin_value: (R, G, B, A)}
        """
        # 清除旧的图例
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 检查是否为分组数据
        # 检查是否为分组数据的逻辑
        # 最终的、可靠的检查逻辑
        is_grouped = False
        if stats_data and isinstance(stats_data, dict):
            # 如果键不全是整数，则认为是分组数据
            if not all(isinstance(k, int) for k in stats_data.keys()):
                is_grouped = True

        if is_grouped:
            for group_name, bin_stats in sorted(stats_data.items()):
                group_title = QLabel(f"<b>Group: {group_name}</b>")
                group_title.setFont(QFont("Arial", 10))
                self.grid_layout.addWidget(group_title)
                self._render_single_legend_block(bin_stats, color_dict)
        else:
            self._render_single_legend_block(stats_data, color_dict)

    def _render_single_legend_block(self, bin_stats, color_dict):
        """渲染单个图例块"""
        if not bin_stats:
            return

        # 排序：PASS在前，FAIL在后
        sorted_bins = sorted(bin_stats.items(),
                           key=lambda x: (not x[1]['is_pass'], x[0]))
        
        row_widget = None
        row_layout = None
        
        for idx, (bin_val, stats) in enumerate(sorted_bins):
            if idx % 8 == 0:
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(3)
                self.grid_layout.addWidget(row_widget)
            
            bin_item = QWidget()
            bin_item.setFixedWidth(120)
            bin_layout = QHBoxLayout(bin_item)
            bin_layout.setContentsMargins(1, 1, 1, 1)
            bin_layout.setSpacing(2)
            
            color_label = QLabel()
            color_label.setFixedSize(12, 12)
            if bin_val in color_dict:
                r, g, b, a = color_dict[bin_val]
                color_label.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); border: 1px solid black;")
            bin_layout.addWidget(color_label)
            
            info_text = f"B{bin_val} {stats['percentage']:.1f}% {stats['count']}"
            info_label = QLabel(info_text)
            info_label.setFont(QFont("Arial", 9))
            bin_layout.addWidget(info_label)
            
            row_layout.addWidget(bin_item)
        
        if row_layout:
            last_row_count = len(sorted_bins) % 8
            if last_row_count > 0:
                for _ in range(8 - last_row_count):
                    spacer = QWidget()
                    spacer.setFixedWidth(120)
                    row_layout.addWidget(spacer)


class MappingChart(UnitChartWindow):
    """
    Mapping图表组件 - 显示芯片在wafer上的分布
    """
    
    def __init__(self, li: Li):
        super(MappingChart, self).__init__()
        self.li = li
        
        # 坐标范围
        self.x_min = 0
        self.y_min = 0
        self.x_max = 0
        self.y_max = 0
        
        # 颜色映射缓存
        self.current_color_dict = {}
        
        # 芯片数据缓存（用于鼠标悬停）
        self.chip_data = {}  # {(x, y): {'bin': int, 'idx': int, 'site': int}}
        
        self.init_ui()
        self.init_coord()
        
        # 连接信号
        if self.li:
            self.li.QChartSelect.connect(self.li_chart_signal)
            self.li.QChartRefresh.connect(self.li_chart_signal)

    def init_ui(self):
        """初始化UI界面"""
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        # 主布局
        main_layout = QVBoxLayout(self.main_widget)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        # 标题标签
        self.title_label = QLabel("Wafer Mapping")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.title_label.setFont(font)
        control_layout.addWidget(self.title_label)
        
        control_layout.addStretch()
        
        # First/Final Test 选择器
        self.test_type_combo = QComboBox()
        self.test_type_combo.addItems(["Final Test", "First Test"])
        self.test_type_combo.currentIndexChanged.connect(self.refresh_mapping)
        control_layout.addWidget(self.test_type_combo)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_mapping)
        control_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(control_layout)
        
        # 图表区域
        self.graphics_widget = GraphicsLayoutWidget()
        main_layout.addWidget(self.graphics_widget, stretch=4)
        
        # 图例区域（在下方）
        self.legend_widget = BinLegendWidget()
        main_layout.addWidget(self.legend_widget, stretch=1)

        # 设置窗口标题
        self.setWindowTitle("Wafer Mapping")

    def init_coord(self):
        """初始化坐标范围"""
        try:
            if self.li and hasattr(self.li, 'to_chart_csv_data') and self.li.to_chart_csv_data is not None:
                df = self.li.to_chart_csv_data.df
                if df is not None and 'X_COORD' in df.columns and 'Y_COORD' in df.columns:
                    # 过滤有效坐标
                    valid_x = df.X_COORD.dropna()
                    valid_y = df.Y_COORD.dropna()
                    if len(valid_x) > 0 and len(valid_y) > 0:
                        self.x_min = int(valid_x.min())
                        self.y_min = int(valid_y.min())
                        self.x_max = int(valid_x.max())
                        self.y_max = int(valid_y.max())
                    else:
                        # 默认坐标范围
                        self.x_min, self.y_min = 0, 0
                        self.x_max, self.y_max = 10, 10
                else:
                    # 默认坐标范围
                    self.x_min, self.y_min = 0, 0
                    self.x_max, self.y_max = 10, 10
            else:
                # 默认坐标范围
                self.x_min, self.y_min = 0, 0
                self.x_max, self.y_max = 10, 10
        except Exception as e:
            print(f"初始化坐标范围失败: {e}")
            # 默认坐标范围
            self.x_min, self.y_min = 0, 0
            self.x_max, self.y_max = 10, 10

    @Slot()
    def refresh_mapping(self):
        """刷新Mapping图"""
        self.generate_mapping()

    def li_chart_signal(self):
        """响应Li的图表信号"""
        if self.action_signal_binding.isChecked():
            self.refresh_mapping()

    def _calculate_bin_statistics(self, data_df, mapping_col):
        """
        计算bin统计信息.
        
        返回:
            bin_stats: {bin_value: {'count': int, 'percentage': float, 'is_pass': bool}}
        """
        if data_df.empty or mapping_col not in data_df.columns:
            return {}

        bin_stats = {}
        total_count = len(data_df)
        
        if total_count == 0:
            return bin_stats
        
        # 基于传入的数据进行统计
        bin_counts = data_df[mapping_col].value_counts()
        
        for bin_val, count in bin_counts.items():
            if pd.isna(bin_val):
                continue
            
            # 获取该bin的FAIL_FLAG (以第一个为代表)
            is_pass = False
            if 'FAIL_FLAG' in data_df.columns:
                fail_flag_series = data_df[data_df[mapping_col] == bin_val]['FAIL_FLAG']
                if not fail_flag_series.empty:
                    is_pass = fail_flag_series.iloc[0] == 1

            percentage = (count / total_count) * 100
            
            bin_stats[int(bin_val)] = {
                'count': count,
                'percentage': percentage,
                'is_pass': is_pass
            }
        
        return bin_stats

    def set_data(self):
        """设置数据并刷新"""
        # 恢复默认标题
        default_title = "Wafer Mapping"
        self.title_label.setText(default_title)
        self.setWindowTitle(default_title)
        
        self.init_coord()
        self.refresh_mapping()

    def generate_mapping(self):
        """生成Mapping图"""
        try:
            # 检查窗口是否已关闭
            if not self.graphics_widget or not hasattr(self.graphics_widget, 'addPlot'):
                return
                
            if not self.li or not hasattr(self.li, 'to_chart_csv_data') or self.li.to_chart_csv_data is None:
                return

            source_df = None
            if hasattr(self.li.to_chart_csv_data, 'chart_df') and self.li.to_chart_csv_data.chart_df is not None:
                source_df = self.li.to_chart_csv_data.chart_df.copy()
            elif hasattr(self.li.to_chart_csv_data, 'df') and self.li.to_chart_csv_data.df is not None:
                source_df = self.li.to_chart_csv_data.df.copy()

            if source_df is None or len(source_df) == 0:
                return

            required_cols = ['X_COORD', 'Y_COORD']
            missing_cols = [col for col in required_cols if col not in source_df.columns]
            if missing_cols:
                return

            mapping_col = 'SOFT_BIN'
            if mapping_col not in source_df.columns:
                return

            self.graphics_widget.clear()

            if 'GROUP' in source_df.columns and len(source_df['GROUP'].unique()) > 1:
                self._generate_grouped_mapping(source_df, mapping_col)
            else:
                self._generate_single_mapping(source_df, mapping_col)

        except RuntimeError:
            pass
        except Exception as e:
            print(f"生成Mapping图失败: {e}")


    def _generate_single_mapping(self, data_df, mapping_col):
        """生成单个Mapping图 - 竖条散点快速渲染（动态调整大小）"""
        # 根据选择器过滤数据
        test_type = self.test_type_combo.currentText()
        keep_option = 'last' if test_type == 'Final Test' else 'first'
        data_df = data_df.drop_duplicates(subset=['X_COORD', 'Y_COORD'], keep=keep_option)
        
        bin_stats = self._calculate_bin_statistics(data_df, mapping_col)
        
        bin_values = data_df[mapping_col].dropna().values
        fail_flags = data_df.loc[data_df[mapping_col].notna(), 'FAIL_FLAG'].values if 'FAIL_FLAG' in data_df.columns else np.ones(len(bin_values))
        
        _, self.current_color_dict = create_dynamic_colormap(bin_values, fail_flags, "SOFT_BIN")
        
        self.chip_data = {}
        has_site = 'SITE_NUM' in data_df.columns
        
        plot_item = self.graphics_widget.addPlot()
        plot_item.invertY(True)
        plot_item.hideAxis('bottom')
        plot_item.hideAxis('left')
        
        scatter_pos = []
        scatter_brushes = []
        
        valid_mask = ~(np.isnan(data_df.X_COORD.values) | np.isnan(data_df.Y_COORD.values) | np.isnan(data_df[mapping_col].values))
        
        if np.any(valid_mask):
            valid_indices = np.where(valid_mask)[0]
            
            for idx in valid_indices:
                x = int(data_df.X_COORD.iloc[idx])
                y = int(data_df.Y_COORD.iloc[idx])
                bin_val = int(data_df[mapping_col].iloc[idx])
                
                site = "N/A"
                if has_site:
                    try:
                        site_val = data_df['SITE_NUM'].iloc[idx]
                        if not pd.isna(site_val):
                            site = str(site_val)
                    except (KeyError, IndexError):
                        pass
                
                self.chip_data[(x, y)] = {'bin': bin_val, 'idx': idx, 'site': site}
                scatter_pos.append((x, y))
                
                if bin_val in self.current_color_dict:
                    r, g, b, a = self.current_color_dict[bin_val]
                    scatter_brushes.append(pg.mkBrush(r, g, b, a))
                else:
                    scatter_brushes.append(pg.mkBrush(128, 128, 128, 255))
        
        # 计算长条大小（使用数据坐标系）
        x_range = self.x_max - self.x_min
        y_range = self.y_max - self.y_min
        
        # 芯片间距（假设芯片间距为1个单位）
        chip_spacing = 1.0
        
        if scatter_pos:
            from pyqtgraph import QtGui
            path = QtGui.QPainterPath()
            # 长条形：宽度0.25单位，高度0.8单位（数据坐标系）
            bar_width = chip_spacing * 0.25
            bar_height = chip_spacing * 0.8
            path.addRect(-bar_width/2, -bar_height/2, bar_width, bar_height)
            
            scatter = pg.ScatterPlotItem(
                pos=scatter_pos,
                brush=scatter_brushes,
                pen=None,  # 去掉黑边框
                size=bar_height,
                symbol=path,
                pxMode=False
            )
            plot_item.addItem(scatter)
        
        x_center = (self.x_min + self.x_max) / 2
        y_center = (self.y_min + self.y_max) / 2
        wafer_diameter = max(x_range, y_range)
        radius = wafer_diameter / 2 * 1.15
        
        plot_item.setXRange(x_center - radius, x_center + radius, padding=0.05)
        plot_item.setYRange(y_center - radius, y_center + radius, padding=0.05)
        plot_item.setAspectLocked(False)
        plot_item.setMouseEnabled(x=True, y=True)
        plot_item.autoRange()  # 首次生成后自动调整
        
        self.tooltip_label = pg.TextItem(
            text="", anchor=(0, 1), color=(0, 0, 0),
            fill=pg.mkBrush(255, 255, 255, 230),
            border=pg.mkPen(0, 0, 0, width=1)
        )
        plot_item.addItem(self.tooltip_label)
        self.tooltip_label.setVisible(False)
        plot_item.scene().sigMouseMoved.connect(lambda pos: self._on_mouse_moved(pos, plot_item))
        
        self.legend_widget.update_legend(bin_stats, self.current_color_dict)
    
    def _on_mouse_moved(self, pos, plot_item):
        """鼠标移动事件 - 显示tooltip"""
        if plot_item.sceneBoundingRect().contains(pos):
            mouse_point = plot_item.vb.mapSceneToView(pos)
            x, y = int(round(mouse_point.x())), int(round(mouse_point.y()))
            
            if (x, y) in self.chip_data:
                data = self.chip_data[(x, y)]
                tooltip_text = f"X: {x}\nY: {y}\nBin: {data['bin']}\nSite: {data['site']}\nIDX: {data['idx']}"
                self.tooltip_label.setText(tooltip_text)
                self.tooltip_label.setPos(mouse_point.x(), mouse_point.y())
                self.tooltip_label.setVisible(True)
            else:
                self.tooltip_label.setVisible(False)
        else:
            self.tooltip_label.setVisible(False)

    def _generate_grouped_mapping(self, data_df, mapping_col):
        """生成分组Mapping图 - 竖条散点（动态调整大小）"""
        test_type = self.test_type_combo.currentText()
        keep_option = 'last' if test_type == 'Final Test' else 'first'

        map_groups = data_df.groupby("GROUP")

        if len(map_groups) > 16:
            map_groups = dict(list(map_groups)[:16])

        num_groups = len(map_groups)
        cols = min(4, num_groups)
        rows = math.ceil(num_groups / cols)

        # 颜色映射基于所有数据，确保颜色一致性
        bin_values = data_df[mapping_col].dropna().values
        fail_flags = data_df.loc[data_df[mapping_col].notna(), 'FAIL_FLAG'].values if 'FAIL_FLAG' in data_df.columns else np.ones(len(bin_values))
        _, self.current_color_dict = create_dynamic_colormap(bin_values, fail_flags, "SOFT_BIN")

        all_group_stats = {}
        chip_spacing = 1.0

        for idx, (group_name, group_df) in enumerate(map_groups):
            # 在每个组内部进行数据筛选
            filtered_group_df = group_df.drop_duplicates(subset=['X_COORD', 'Y_COORD'], keep=keep_option)
            
            # 为每个组计算独立的统计数据
            group_bin_stats = self._calculate_bin_statistics(filtered_group_df, mapping_col)
            all_group_stats[group_name] = group_bin_stats

            row = idx // cols
            col = idx % cols

            plot_item = self.graphics_widget.addPlot(row=row, col=col, title=f"Group {group_name}")
            plot_item.invertY(True)
            plot_item.hideAxis('bottom')
            plot_item.hideAxis('left')
            
            scatter_pos = []
            scatter_brushes = []
            
            # 使用筛选后的数据进行绘图
            valid_mask = ~(np.isnan(filtered_group_df.X_COORD.values) | np.isnan(filtered_group_df.Y_COORD.values) | np.isnan(filtered_group_df[mapping_col].values))
            if np.any(valid_mask):
                valid_indices = np.where(valid_mask)[0]
                
                for i in valid_indices:
                    x = int(filtered_group_df.X_COORD.iloc[i])
                    y = int(filtered_group_df.Y_COORD.iloc[i])
                    bin_val = int(filtered_group_df[mapping_col].iloc[i])
                    
                    scatter_pos.append((x, y))
                    
                    if bin_val in self.current_color_dict:
                        r, g, b, a = self.current_color_dict[bin_val]
                        scatter_brushes.append(pg.mkBrush(r, g, b, a))
                    else:
                        scatter_brushes.append(pg.mkBrush(128, 128, 128, 255))
            
            if scatter_pos:
                from pyqtgraph import QtGui
                path = QtGui.QPainterPath()
                bar_width = chip_spacing * 0.25
                bar_height = chip_spacing * 0.8
                path.addRect(-bar_width/2, -bar_height/2, bar_width, bar_height)
                
                scatter = pg.ScatterPlotItem(
                    pos=scatter_pos,
                    brush=scatter_brushes,
                    pen=None,
                    size=bar_height,
                    symbol=path,
                    pxMode=False
                )
                plot_item.addItem(scatter)
            
            x_center = (self.x_min + self.x_max) / 2
            y_center = (self.y_min + self.y_max) / 2
            x_range = self.x_max - self.x_min
            y_range = self.y_max - self.y_min
            wafer_diameter = max(x_range, y_range)
            radius = wafer_diameter / 2 * 1.15
            
            plot_item.setXRange(x_center - radius, x_center + radius, padding=0.05)
            plot_item.setYRange(y_center - radius, y_center + radius, padding=0.05)
            plot_item.setAspectLocked(False)
            plot_item.setMouseEnabled(x=True, y=True)
            plot_item.autoRange()
        
        # 使用新的图例方法显示所有分组的统计
        self.legend_widget.update_legend(all_group_stats, self.current_color_dict)

    def closeEvent(self, event):
        """关闭事件处理"""
        try:
            if self.li:
                self.li.QChartSelect.disconnect(self.li_chart_signal)
                self.li.QChartRefresh.disconnect(self.li_chart_signal)
        except RuntimeError:
            pass
        super().closeEvent(event)
