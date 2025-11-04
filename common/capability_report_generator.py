#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : capability_report_generator.py
@Author  : Link
@Time    : 2025/10/30
@Mark    : 制程能力报告生成器
"""
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np


class CapabilityReportGenerator:
    """
    制程能力报告生成器
    用于生成综合报告和单文件报告
    """
    
    @staticmethod
    def filter_valid_items(capability_list: List[dict]) -> List[dict]:
        """
        筛选有效的测项（有limit且可评估CPK）
        
        筛选条件：
        1. 必须有CPK值（不是NaN）
        2. 必须有上限或下限（至少有一个）
        
        :param capability_list: 制程能力数据列表
        :return: 筛选后的列表
        """
        valid_items = []
        
        for item in capability_list:
            cpk = item.get('CPK', np.nan)
            lo_limit = item.get('LO_LIMIT', np.nan)
            hi_limit = item.get('HI_LIMIT', np.nan)
            
            # 检查是否有有效的CPK值
            if pd.isna(cpk):
                continue
            
            # 检查是否至少有一个limit
            has_limit = False
            if not pd.isna(lo_limit) and lo_limit != 0:
                has_limit = True
            if not pd.isna(hi_limit) and hi_limit != 0:
                has_limit = True
            
            if has_limit:
                valid_items.append(item)
        
        return valid_items
    
    @staticmethod
    def sort_by_cpk(capability_list: List[dict], ascending: bool = True) -> List[dict]:
        """
        按CPK大小排序
        
        :param capability_list: 制程能力数据列表
        :param ascending: True=升序（CPK从小到大），False=降序（CPK从大到小）
        :return: 排序后的列表
        """
        # 创建副本，避免修改原始数据
        sorted_list = capability_list.copy()
        
        # 按CPK排序，NaN值放在最后
        sorted_list.sort(
            key=lambda x: (pd.isna(x.get('CPK', np.nan)), x.get('CPK', np.nan)),
            reverse=not ascending
        )
        
        return sorted_list
    
    @staticmethod
    def generate_summary_statistics(capability_list: List[dict]) -> Dict:
        """
        生成统计摘要
        
        :param capability_list: 制程能力数据列表
        :return: 统计摘要字典
        """
        if not capability_list:
            return {
                'total_items': 0,
                'cpk_avg': np.nan,
                'cpk_min': np.nan,
                'cpk_max': np.nan,
                'cpk_lt_1': 0,
                'cpk_1_to_1_33': 0,
                'cpk_gt_1_33': 0,
                'sigma_avg': np.nan,
            }
        
        cpk_values = [item['CPK'] for item in capability_list if not pd.isna(item.get('CPK'))]
        sigma_values = [item['SIGMA_LEVEL'] for item in capability_list if not pd.isna(item.get('SIGMA_LEVEL'))]
        
        # CPK分级统计
        cpk_lt_1 = sum(1 for cpk in cpk_values if cpk < 1.0)
        cpk_1_to_1_33 = sum(1 for cpk in cpk_values if 1.0 <= cpk < 1.33)
        cpk_gt_1_33 = sum(1 for cpk in cpk_values if cpk >= 1.33)
        
        return {
            'total_items': len(capability_list),
            'cpk_avg': round(np.mean(cpk_values), 3) if cpk_values else np.nan,
            'cpk_min': round(np.min(cpk_values), 3) if cpk_values else np.nan,
            'cpk_max': round(np.max(cpk_values), 3) if cpk_values else np.nan,
            'cpk_lt_1': cpk_lt_1,
            'cpk_1_to_1_33': cpk_1_to_1_33,
            'cpk_gt_1_33': cpk_gt_1_33,
            'sigma_avg': round(np.mean(sigma_values), 2) if sigma_values else np.nan,
        }
    
    @staticmethod
    def format_summary_text(stats: Dict) -> str:
        """
        格式化统计摘要为文本
        
        :param stats: 统计摘要字典
        :return: 格式化的文本
        """
        text = f"""
╔══════════════════════════════════════════════════════════════╗
║                    制程能力统计摘要                          ║
╠══════════════════════════════════════════════════════════════╣
║  总测项数量: {stats['total_items']:>6}                                      ║
║  CPK 平均值: {stats['cpk_avg']:>6.3f}                                      ║
║  CPK 最小值: {stats['cpk_min']:>6.3f}                                      ║
║  CPK 最大值: {stats['cpk_max']:>6.3f}                                      ║
║  Sigma 平均: {stats['sigma_avg']:>6.2f}                                      ║
╠══════════════════════════════════════════════════════════════╣
║  CPK 分级统计:                                               ║
║    CPK < 1.0    : {stats['cpk_lt_1']:>4} 项 ({stats['cpk_lt_1']/stats['total_items']*100:>5.1f}%)                  ║
║    1.0 ≤ CPK < 1.33: {stats['cpk_1_to_1_33']:>4} 项 ({stats['cpk_1_to_1_33']/stats['total_items']*100:>5.1f}%)                  ║
║    CPK ≥ 1.33   : {stats['cpk_gt_1_33']:>4} 项 ({stats['cpk_gt_1_33']/stats['total_items']*100:>5.1f}%)                  ║
╚══════════════════════════════════════════════════════════════╝
"""
        return text
    
    @staticmethod
    def create_dataframe(capability_list: List[dict]) -> pd.DataFrame:
        """
        创建DataFrame用于显示
        
        :param capability_list: 制程能力数据列表
        :return: DataFrame
        """
        if not capability_list:
            return pd.DataFrame()
        
        # 选择要显示的列
        columns = [
            'TEST_NUM', 'TEST_TXT', 'UNITS',
            'LO_LIMIT', 'HI_LIMIT',
            'AVG', 'STD', 'MEDIAN',
            'CPK', 'CP', 'PPK', 'PP', 'SIGMA_LEVEL',
            'QTY', 'FAIL_QTY', 'FAIL_RATE',
            'MIN', 'MAX'
        ]
        
        # 创建DataFrame
        df = pd.DataFrame(capability_list)
        
        # 只保留存在的列
        existing_columns = [col for col in columns if col in df.columns]
        df = df[existing_columns]
        
        # 重命名列（中文）
        column_names = {
            'TEST_NUM': '测项编号',
            'TEST_TXT': '测项名称',
            'UNITS': '单位',
            'LO_LIMIT': '下限',
            'HI_LIMIT': '上限',
            'AVG': '平均值',
            'STD': '标准差',
            'MEDIAN': '中位数',
            'CPK': 'Cpk',
            'CP': 'Cp',
            'PPK': 'Ppk',
            'PP': 'Pp',
            'SIGMA_LEVEL': 'Sigma',
            'QTY': '数量',
            'FAIL_QTY': 'Fail数',
            'FAIL_RATE': 'Fail率',
            'MIN': '最小值',
            'MAX': '最大值',
        }
        
        df = df.rename(columns=column_names)
        
        return df
    
    @staticmethod
    def get_cpk_distribution_data(capability_list: List[dict]) -> Tuple[List[float], List[str]]:
        """
        获取CPK分布数据（用于绘制分布图）
        
        :param capability_list: 制程能力数据列表
        :return: (CPK值列表, 测项名称列表)
        """
        cpk_values = []
        test_names = []
        
        for item in capability_list:
            cpk = item.get('CPK', np.nan)
            if not pd.isna(cpk):
                cpk_values.append(cpk)
                test_names.append(f"{item.get('TEST_NUM', '')}:{item.get('TEST_TXT', '')}")
        
        return cpk_values, test_names
    
    @staticmethod
    def get_pareto_data(capability_list: List[dict], top_n: int = 20) -> Tuple[List[str], List[float], List[int]]:
        """
        获取帕累托图数据（按CPK从小到大排序，取前N项）
        
        :param capability_list: 制程能力数据列表
        :param top_n: 显示前N项
        :return: (测项名称列表, CPK值列表, Fail数量列表)
        """
        # 按CPK升序排序
        sorted_list = CapabilityReportGenerator.sort_by_cpk(capability_list, ascending=True)
        
        # 取前N项
        top_items = sorted_list[:top_n]
        
        test_names = []
        cpk_values = []
        fail_counts = []
        
        for item in top_items:
            test_names.append(f"{item.get('TEST_NUM', '')}:{item.get('TEST_TXT', '')}")
            cpk_values.append(item.get('CPK', 0))
            fail_counts.append(item.get('FAIL_QTY', 0))
        
        return test_names, cpk_values, fail_counts

