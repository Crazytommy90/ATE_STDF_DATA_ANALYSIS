"""
-*- coding: utf-8 -*-
@Author  : Link
@Time    : 2022/5/12 13:53
@Software: PyCharm
@File    : chart_trans_bar.py
@Remark  : 
"""

import math
from typing import List, Union, Tuple, Any

import numpy as np
import pandas as pd
from PySide2 import QtCore
from PySide2.QtCore import Qt
from PySide2.QtGui import QCloseEvent
from pyqtgraph import InfiniteLine, BarGraphItem

from app_test.test_utils.wrapper_utils import Time
from chart_core.chart_pyqtgraph.core.mixin import BasePlot, GraphRangeSignal, PlotWidget, RangeData
from chart_core.chart_pyqtgraph.core.view_box import CustomViewBox
from chart_core.chart_pyqtgraph.ui_components.ui_unit_chart import UnitChartWindow
from common.li import Li
from ui_component.ui_app_variable import UiGlobalVariable


class TransBarChart(UnitChartWindow, BasePlot):
    """
    横向柱状图, 用新的数据类型后, 运行时间长的有点过分了/(ㄒoㄒ)/~~
        TODO: rota: 0b000000
            0bX_____ -> select x  选取后筛选X轴的数据
            0b_X____ -> select y  选取后筛选Y轴的数据
            0b__X___ -> lint x    H_L_Limit/AVG 放在X轴 -> 主要数据分布在X上
            0b___X__ -> lint y    H_L_Limit/AVG 放在Y轴 -> 主要数据分布在Y上
            0b____X_ -> zoom x    X轴放大缩小
            0b_____X -> zoom y    Y轴放大缩小
    """

    bar_width: float = 0  # 这个是柱状图的当前宽度
    ticks: list = None  # X轴
    list_bins: Union[Tuple[np.ndarray, Any], np.ndarray] = None
    chart_v_lines: List[InfiniteLine] = None
    limit_lines: List[InfiniteLine] = None  # limit线列表
    bar_items: List[BarGraphItem] = None # 用于存储动态创建的BarGraphItem

    def __init__(self, li: Li):
        super(TransBarChart, self).__init__()
        self.li = li
        self.p_range = RangeData()
        self.rota = 0b010101
        self.sig = 0 if self.rota & 0b1000 else 1

        self.vb = CustomViewBox()
        self.pw = PlotWidget(viewBox=self.vb, enableMenu=False)
        self.setCentralWidget(self.pw)
        self.pw.hideButtons()

        self.legend = self.pw.addLegend()
        self.legend.anchor((1, 0), (1, 0))  # (1,0) is the top-right corner

        self.bottom_axis = self.pw.getAxis("bottom")
        self.bottom_axis.setHeight(60)
        self.left_axis = self.pw.getAxis("left")
        self.left_axis.setWidth(60)

        self.pw.setMouseEnabled(x=False, y=True) # 允许Y轴缩放
        self.vb.select_signal.connect(self.select_range)
        self.li.QChartSelect.connect(self.li_chart_signal)
        self.li.QChartRefresh.connect(self.li_chart_signal)

        self.chart_v_lines = []
        self.limit_lines = []
        self.bar_items = []

    def init_movable_line(self):
        h_line = InfiniteLine(angle=0, movable=False, label='y={value:0.5f}', labelOpts={'color': (0, 0, 0)})
        self.vb.addItem(h_line, ignoreBounds=True)

        def mouseMoved(evt):
            if self.vb.sceneBoundingRect().contains(evt):
                mouse_point = self.vb.mapSceneToView(evt)
                h_line.setPos(mouse_point.y())

        self.vb.scene().sigMouseMoved.connect(mouseMoved)

    def li_chart_signal(self):
        if self.action_signal_binding.isChecked():
            self.set_front_chart()

    def select_range(self, axs: Union[List[QtCore.QRectF], None]):
        """
        区间选取后触发,更新chart_df
        :return:
        """
        if not self.action_signal_binding.isChecked():
            return
        if axs is None:
            """
            show all front
            """
            self.li.set_chart_data(None)
            return
        chart_prr_list = []
        for ax in axs:
            """
            1. 选取X轴
            2. 选取Y轴
            """
            select_start = math.ceil(ax.left() / self.bar_width)
            select_stop = math.ceil(ax.right() / self.bar_width)
            if select_start > len(self.ticks) or select_stop < 0:
                continue

            keys = []
            for i in range(select_start - 1, select_stop):
                if i < 0:
                    continue
                if i == len(self.ticks):
                    break
                key = self.ticks[i]
                keys.append(key)
            for key in keys:
                temp = self.li.to_chart_csv_data.group_df[key]
                if len(temp) == 0:
                    continue
                result_min, result_max = ax.top(), ax.bottom()
                chart_prr = temp[
                    (temp[self.key] > result_min) & (temp[self.key] < result_max)
                    ]
                chart_prr_list.append(chart_prr)

        self.li.set_chart_data(pd.concat(chart_prr_list))

    def set_range_data_to_chart(self, a, ax) -> bool:
        if hasattr(self, 'vb'):
            self.update_legend_position()
        res = super(TransBarChart, self).set_range_data_to_chart(a, ax)
        if res:
            self.set_front_chart()
        return res

    @Time()
    @GraphRangeSignal
    def set_df_chart(self):
        """
        即使某个Group内没有数据, 也要给留出位置
        :return:
        """
        if self.li.to_chart_csv_data.df is None:
            return
        if self.key not in self.li.capability_key_dict:
            return

        # 清理旧的图表元素
        self._clear_plot_items()

        # 定义颜色列表
        colors = [
            (217, 83, 25, 150), (0, 114, 189, 150), (237, 177, 32, 150),
            (126, 47, 142, 150), (119, 172, 48, 150), (77, 190, 238, 150),
            (162, 20, 47, 150)
        ]
        color_index = 0

        # 处理y_min和y_max相同的情况
        y_min, y_max = self.p_range.y_min, self.p_range.y_max
        if y_min == y_max:
            if y_min == 0:
                y_min, y_max = -0.1, 0.1
            else:
                offset = abs(y_min) * 0.1 if abs(y_min) > 0 else 0.1
                y_min, y_max = y_min - offset, y_max + offset

        self.list_bins = np.linspace(y_min, y_max, UiGlobalVariable.GraphBins)
        bin_centers = (self.list_bins[:-1] + self.list_bins[1:]) / 2
        bin_height = self.list_bins[1] - self.list_bins[0]

        # 检查是否有分组
        group_keys = self.li.to_chart_csv_data.group_df.keys()
        has_grouping = len(group_keys) > 1 or next(iter(group_keys), "*@*") != "*@*"

        if not has_grouping:
            # 无分组逻辑
            df = self.li.to_chart_csv_data.df
            temp_dis = df[self.key].value_counts(bins=self.list_bins, sort=False)
            bar_item = BarGraphItem(x0=0, y=bin_centers, width=temp_dis.values, height=bin_height,
                                    brush=colors[0], name="All Data")
            self.pw.addItem(bar_item)
            self.bar_items.append(bar_item)
        else:
            # 有分组逻辑
            for key, df in self.li.to_chart_csv_data.group_df.items():
                if self.li.to_chart_csv_data.select_group is not None:
                    if key not in self.li.to_chart_csv_data.select_group:
                        continue
                if len(df) == 0:
                    continue
                
                temp_dis = df[self.key].value_counts(bins=self.list_bins, sort=False)
                if len(temp_dis) == 0:
                    continue

                color = colors[color_index % len(colors)]
                color_index += 1
                
                bar_item = BarGraphItem(x0=0, y=bin_centers, width=temp_dis.values, height=bin_height,
                                        brush=color, name=key)
                self.pw.addItem(bar_item)
                self.bar_items.append(bar_item)

        self.bottom_axis.setLabel("Count")
        self.left_axis.setLabel("Value")
        self.bottom_axis.setTicks(None) # 使用默认刻度

        # 添加limit线显示
        self._add_limit_lines()

        if not self.change:
            self.vb.setYRange(y_min, y_max)
            self.change = True
    
            # 更新图例位置
            self.update_legend_position()

    def _add_limit_lines(self):
        """
        添加LO_LIMIT、HI_LIMIT、NEW_LO_LIMIT、NEW_HI_LIMIT显示线
        """
        if self.key not in self.li.capability_key_dict:
            return

        capability_info = self.li.capability_key_dict[self.key]

        # 获取limit值
        lo_limit = capability_info.get('LO_LIMIT')
        hi_limit = capability_info.get('HI_LIMIT')
        new_lo_limit = capability_info.get('NEW_LO_LIMIT')
        new_hi_limit = capability_info.get('NEW_HI_LIMIT')

        # 添加原始LO_LIMIT线（蓝色虚线）
        if lo_limit is not None:
            lo_line = InfiniteLine(
                angle=0,
                movable=False,
                pen={'color': (0, 100, 255), 'width': 2, 'style': Qt.DashLine},  # 蓝色虚线
                label='LO_LIMIT={value:0.6f}',
                labelOpts={'position': 0.95, 'color': (0, 100, 255), 'fill': (255, 255, 255, 150)}
            )
            self.vb.addItem(lo_line, ignoreBounds=True)
            lo_line.setPos(lo_limit)
            self.limit_lines.append(lo_line)

        # 添加原始HI_LIMIT线（红色虚线）
        if hi_limit is not None:
            hi_line = InfiniteLine(
                angle=0,
                movable=False,
                pen={'color': (255, 50, 50), 'width': 2, 'style': Qt.DashLine},  # 红色虚线
                label='HI_LIMIT={value:0.6f}',
                labelOpts={'position': 0.95, 'color': (255, 50, 50), 'fill': (255, 255, 255, 150)}
            )
            self.vb.addItem(hi_line, ignoreBounds=True)
            hi_line.setPos(hi_limit)
            self.limit_lines.append(hi_line)

        # 如果有新的limit值且与原始值不同，添加新limit线
        if new_lo_limit is not None and lo_limit is not None:
            if abs(new_lo_limit - lo_limit) > 1e-9:
                new_lo_line = InfiniteLine(
                    angle=0,
                    movable=False,
                    pen={'color': (0, 200, 100), 'width': 2, 'style': Qt.SolidLine},  # 绿色实线
                    label='NEW_LO_LIMIT={value:0.6f}',
                    labelOpts={'position': 0.05, 'color': (0, 200, 100), 'fill': (255, 255, 255, 150)}
                )
                self.vb.addItem(new_lo_line, ignoreBounds=True)
                new_lo_line.setPos(new_lo_limit)
                self.limit_lines.append(new_lo_line)

        if new_hi_limit is not None and hi_limit is not None:
            if abs(new_hi_limit - hi_limit) > 1e-9:
                new_hi_line = InfiniteLine(
                    angle=0,
                    movable=False,
                    pen={'color': (255, 150, 0), 'width': 2, 'style': Qt.SolidLine},  # 橙色实线
                    label='NEW_HI_LIMIT={value:0.6f}',
                    labelOpts={'position': 0.05, 'color': (255, 150, 0), 'fill': (255, 255, 255, 150)}
                )
                self.vb.addItem(new_hi_line, ignoreBounds=True)
                new_hi_line.setPos(new_hi_limit)
                self.limit_lines.append(new_hi_line)
        
    def update_legend_position(self):
        """
        根据limit线的位置动态调整legend的位置, 防止遮挡
        """
        if not hasattr(self, 'legend') or self.legend is None:
            return

        # 获取视图的Y轴范围
        view_y_range = self.vb.viewRange()[1]
        view_y_min, view_y_max = view_y_range

        # 获取所有HI_LIMIT线的值
        hi_limits = []
        if self.key in self.li.capability_key_dict:
            capability_info = self.li.capability_key_dict[self.key]
            hi_limit = capability_info.get('HI_LIMIT')
            new_hi_limit = capability_info.get('NEW_HI_LIMIT')
            if hi_limit is not None:
                hi_limits.append(hi_limit)
            if new_hi_limit is not None:
                hi_limits.append(new_hi_limit)

        # 检查是否有limit线与legend重叠
        overlap = False
        if hi_limits:
            # 根据图例中的项目数量动态计算高度比例
            num_items = len(self.legend.items)
            base_ratio = 0.1  # 基础高度比例
            ratio_per_item = 0.05  # 每个项目的额外比例
            legend_height_ratio = base_ratio + num_items * ratio_per_item
            
            legend_y_min = view_y_max - (view_y_max - view_y_min) * legend_height_ratio
            
            for limit in hi_limits:
                if limit > legend_y_min and limit < view_y_max:
                    overlap = True
                    break
        
        if overlap:
            # 如果重叠，将图例移动到右下角
            self.legend.anchor((1, 1), (1, 1))
        else:
            # 否则，保持在右上角
            self.legend.anchor((1, 0), (1, 0))

    @Time()
    def _clear_plot_items(self):
        """清理图表上的所有项目"""
        for item in self.bar_items:
            self.pw.removeItem(item)
        self.bar_items.clear()

        for v_line in self.chart_v_lines:
            self.vb.removeItem(v_line)
        self.chart_v_lines.clear()

        for limit_line in self.limit_lines:
            self.vb.removeItem(limit_line)
        self.limit_lines.clear()

    def set_front_chart(self):
        # self.bg2.setOpts(x0=[], y=[], y0=[], y1=[], width=[]) # bg2 is removed
        self.set_df_chart()
        # The rest of the logic is now handled within set_df_chart

    def closeEvent(self, event: QCloseEvent) -> None:
        self.__del__()
        super(TransBarChart, self).closeEvent(event)
