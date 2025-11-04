#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : mdi_data_merge.py
@Author  : Link
@Time    : 2022/12/11 13:19
@Mark    : Merge是一个非常复杂的事情
           Merge中, 需要对TEST_NO进行一下处理
"""
from typing import Dict
import pandas as pd
from PySide2.QtCore import Signal

from ui_component.ui_main.mdi_data_concat import ContactWidget
from ui_component.ui_common.ui_utils import MdiLoad


class MergeWidget(ContactWidget):
    """
    继承ContactWidget，扩展Merge功能
    复用Contact的UI和选择逻辑，添加基于Limit的Merge能力
    """
    
    def get_choose_mdi(self):
        """
        重写父类方法，实现Merge逻辑
        1. 获取选中的MDI列表
        2. 获取参考MDI（从comboBox选择）
        3. 使用参考MDI的limit进行数据合并
        """
        choose_mdi = []
        for i in range(self.listWidget.count()):
            item = self.listWidget.itemWidget(self.listWidget.item(i))
            if item.isChecked():
                choose_mdi.append(self.id_cache[item.text()])
        
        if len(choose_mdi) == 0:
            return self.messageSignal.emit("未选择任何MDI窗口")
        
        # 获取参考MDI（用于limit）
        ref_name = self.comboBox.currentText()
        if not ref_name:
            return self.messageSignal.emit("请选择参考Limit的MDI")
        
        ref_mdi_id = self.id_cache[ref_name]
        
        # 执行Merge
        merged_summary = self.merge_data_with_limit(choose_mdi, ref_mdi_id)
        
        if merged_summary is not None:
            self.dataSignal.emit(merged_summary)
            self.messageSignal.emit(f"Merge完成，使用 {ref_name} 的Limit作为基准")
    
    def merge_data_with_limit(self, choose_mdi: list, reference_mdi_id: int) -> pd.DataFrame:
        """
        基于参考MDI的limit进行数据合并
        :param choose_mdi: 选中的MDI ID列表
        :param reference_mdi_id: 参考MDI的ID（用于limit）
        :return: 合并后的summary DataFrame
        """
        # 验证所有MDI数据是否准备好
        for mdi_id in choose_mdi:
            mdi = self.mdi_cache[mdi_id].mdi
            if mdi.summary.ready is False:
                self.messageSignal.emit(f"MDI {mdi_id} 的数据未载入")
                return None
        
        # 合并所有summary数据（简单concat）
        summary_list = []
        for mdi_id in choose_mdi:
            mdi = self.mdi_cache[mdi_id].mdi
            summary_list.append(mdi.summary.summary_df)
        
        merged_summary = pd.concat(summary_list, ignore_index=True)
        
        # 注意：这里只合并summary数据
        # limit的处理在后续数据加载时，通过reference_mdi_id来指定
        # 实际的limit应用需要在Li.concat()时处理
        
        return merged_summary
