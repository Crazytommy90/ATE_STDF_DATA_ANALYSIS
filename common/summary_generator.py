#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : summary_generator.py
@Author  : Link
@Time    : 2025/10/30
@Mark    : Summary报告生成工具类
"""
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from common.app_variable import DataModule


class SummaryGenerator:
    """
    Summary报告生成器
    负责从STDF数据中提取并格式化Summary信息
    """
    
    @staticmethod
    def format_timestamp(timestamp: int) -> str:
        """
        将STDF时间戳转换为可读格式
        :param timestamp: STDF时间戳（秒）
        :return: 格式化的时间字符串 YYYY/MM/DD HH:MM:SS
        """
        if timestamp == 0 or pd.isna(timestamp):
            return "--------"
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y/%m/%d %H:%M:%S")
        except:
            return "--------"
    
    @staticmethod
    def format_temperature(temp) -> str:
        """
        格式化温度显示
        :param temp: 温度值（可能是int、float或str）
        :return: 格式化的温度字符串
        """
        # 处理空值
        if temp is None or pd.isna(temp):
            return "--------"

        # 转换为数值类型
        try:
            temp_value = float(temp)
            if temp_value == 0:
                return "--------"
            return f"{int(temp_value):04d}"
        except (ValueError, TypeError):
            return "--------"
    
    @staticmethod
    def calculate_bin_statistics(prr_df: pd.DataFrame, bin_column: str, bin_name_dict: Optional[Dict] = None) -> List[Dict]:
        """
        计算Bin统计信息
        :param prr_df: PRR DataFrame
        :param bin_column: Bin列名 ('HARD_BIN' 或 'SOFT_BIN')
        :param bin_name_dict: Bin名称字典 {bin_num: bin_name}
        :return: Bin统计列表
        """
        if prr_df is None or len(prr_df) == 0:
            return []

        total_qty = len(prr_df)
        bin_stats = []

        # 按Bin分组统计
        for bin_num, group in prr_df.groupby(bin_column):
            qty = len(group)
            percentage = (qty / total_qty * 100) if total_qty > 0 else 0

            # 确保 bin_num 是整数类型用于比较
            try:
                bin_num_int = int(bin_num)
            except (ValueError, TypeError):
                bin_num_int = bin_num

            # 判断是Pass还是Fail (通常Bin 1是Pass)
            bin_type = "P" if bin_num_int == 1 else "F"

            # 获取Bin名称
            bin_name = bin_name_dict.get(bin_num_int, "") if bin_name_dict else ""

            # 按Site统计 - 只统计有该bin数据的site
            site_stats = {}
            if 'SITE_NUM' in group.columns:
                for site_num in group['SITE_NUM'].unique():
                    # 提取site编号（处理'S001'或数字格式）
                    if isinstance(site_num, str) and site_num.startswith('S'):
                        site_num_int = int(site_num[1:])
                    else:
                        site_num_int = int(site_num)

                    site_bin_df = group[group['SITE_NUM'] == site_num]
                    site_total = len(prr_df[prr_df['SITE_NUM'] == site_num])
                    site_bin_qty = len(site_bin_df)
                    site_bin_percentage = (site_bin_qty / site_total * 100) if site_total > 0 else 0
                    site_stats[site_num_int] = {
                        'QTY': site_bin_qty,
                        'PERCENTAGE': site_bin_percentage
                    }

            bin_stats.append({
                "BIN": bin_num_int,
                "BIN_NAME": bin_name,
                "BIN_TYPE": bin_type,
                "QTY": qty,
                "PERCENTAGE": percentage,
                "SITE_STATS": site_stats
            })

        # 按Bin号排序
        bin_stats.sort(key=lambda x: x["BIN"])
        return bin_stats
    
    @staticmethod
    def calculate_site_statistics(prr_df: pd.DataFrame) -> Dict:
        """
        计算Site级别的统计信息
        :param prr_df: PRR DataFrame
        :return: Site统计字典
        """
        if prr_df is None or len(prr_df) == 0:
            return {}
        
        site_stats = {}
        
        # 全部统计
        total_qty = len(prr_df)
        pass_qty = len(prr_df[prr_df['FAIL_FLAG'] == 1])  # FAIL_FLAG=1表示Pass
        fail_qty = total_qty - pass_qty
        
        site_stats['All'] = {
            'TOTAL': total_qty,
            'PASS': pass_qty,
            'FAIL': fail_qty,
            'PASS_RATE': (pass_qty / total_qty * 100) if total_qty > 0 else 0,
            'FAIL_RATE': (fail_qty / total_qty * 100) if total_qty > 0 else 0
        }
        
        # 按Site统计
        if 'SITE_NUM' in prr_df.columns:
            for site_num, group in prr_df.groupby('SITE_NUM'):
                site_total = len(group)
                site_pass = len(group[group['FAIL_FLAG'] == 1])
                site_fail = site_total - site_pass

                # 提取site编号（处理'S001'或数字格式）
                if isinstance(site_num, str) and site_num.startswith('S'):
                    site_num_int = int(site_num[1:])
                else:
                    site_num_int = int(site_num)
                
                site_key = f'{site_num_int}(S{site_num_int:03d})'

                site_stats[site_key] = {
                    'TOTAL': site_total,
                    'PASS': site_pass,
                    'FAIL': site_fail,
                    'PASS_RATE': (site_pass / site_total * 100) if site_total > 0 else 0,
                    'FAIL_RATE': (site_fail / site_total * 100) if site_total > 0 else 0,
                    'SITE_NUM_INT': site_num_int  # 保存整数编号用于bin统计匹配
                }
        
        return site_stats
    
    @staticmethod
    def calculate_test_time(prr_df: pd.DataFrame) -> Dict:
        """
        计算测试时间统计
        :param prr_df: PRR DataFrame
        :return: 测试时间字典
        """
        if prr_df is None or len(prr_df) == 0 or 'TEST_T' not in prr_df.columns:
            return {'ALL': 0, 'PASS_ONLY': 0}
        
        # TEST_T单位通常是毫秒
        all_test_time = int(prr_df['TEST_T'].mean()) if len(prr_df) > 0 else 0

        pass_df = prr_df[prr_df['FAIL_FLAG'] == 1]
        pass_test_time = int(pass_df['TEST_T'].mean()) if len(pass_df) > 0 else 0
        
        return {
            'ALL': all_test_time,
            'PASS_ONLY': pass_test_time
        }
    
    @staticmethod
    def calculate_retest_statistics(prr_df: pd.DataFrame) -> Dict:
        """
        计算首测/重测统计
        :param prr_df: PRR DataFrame
        :return: 首测/重测统计字典
        """
        if prr_df is None or len(prr_df) == 0 or 'PART_FLG' not in prr_df.columns:
            return {'FRESH': 0, 'RETEST': 0, 'FRESH_RATE': 100.0, 'RETEST_RATE': 0.0}
        
        total_qty = len(prr_df)
        
        # PART_FLG bit 1 表示是否为重测 (0b10 = 2)
        retest_qty = len(prr_df[prr_df['PART_FLG'] & 0b10 == 0b10])
        fresh_qty = total_qty - retest_qty
        
        return {
            'FRESH': fresh_qty,
            'RETEST': retest_qty,
            'FRESH_RATE': (fresh_qty / total_qty * 100) if total_qty > 0 else 0,
            'RETEST_RATE': (retest_qty / total_qty * 100) if total_qty > 0 else 0
        }
    
    @staticmethod
    def generate_summary_text(summary_info: Dict, file_info: Dict, df_module: DataModule) -> str:
        """
        生成Summary文本报告
        :param summary_info: Summary基本信息（从summary_df获取）
        :param file_info: 文件信息
        :param df_module: 数据模块（包含prr_df等）
        :return: 格式化的Summary文本
        """
        lines = []
        
        # ==================== Basic Info ====================
        lines.append("Basic Info")
        lines.append(f"File Path:      {file_info.get('FILE_PATH', '--------')}")
        lines.append(f"File Name:      {file_info.get('FILE_NAME', '--------')}")
        lines.append(f"Lot Number:     {summary_info.get('LOT_ID', '--------'):<16}")
        lines.append(f"Sub Lot:        {summary_info.get('SBLOT_ID', '--------')}")
        lines.append(f"Date Code:      ")
        lines.append(f"Setup Time:     {SummaryGenerator.format_timestamp(summary_info.get('SETUP_T', 0))}")
        lines.append(f"Start Time:     {SummaryGenerator.format_timestamp(summary_info.get('START_T', 0))}")
        lines.append(f"Finish Time:    {file_info.get('FINISH_TIME', '--------')}")
        lines.append(f"Temperature:    {SummaryGenerator.format_temperature(summary_info.get('TST_TEMP', 0))}")
        lines.append(f"Node Name:      {summary_info.get('NODE_NAM', '--------')}")
        lines.append(f"Tester Type:    {file_info.get('TESTER_TYPE', '--------')}")
        lines.append(f"Part Type:      {summary_info.get('PART_TYP', '--------')}")
        lines.append(f"Job Name:       {summary_info.get('JOB_NAM', '--------')}")
        lines.append(f"Exec Type:      {file_info.get('EXEC_TYPE', '--------')}")
        lines.append(f"Exec Ver:       {file_info.get('EXEC_VER', '--------')}")
        lines.append(f"Test Mode:      {file_info.get('TEST_MODE', '--------')}")
        lines.append(f"Station ID:     {file_info.get('STAT_NUM', '--------')}")
        lines.append(f"Operator:       {file_info.get('OPER_NAM', '--------')}")
        lines.append(f"Burn-In:        {file_info.get('BURN_TIM', '--------')}")
        lines.append("")
        
        # ==================== Qty Statistic ====================
        test_time = SummaryGenerator.calculate_test_time(df_module.prr_df)
        site_stats = SummaryGenerator.calculate_site_statistics(df_module.prr_df)
        retest_stats = SummaryGenerator.calculate_retest_statistics(df_module.prr_df)
        
        lines.append("Qty Statistic")
        lines.append(f"Test Time:      {test_time['ALL']} ms")
        lines.append(f"Test Time(Pass Only):{test_time['PASS_ONLY']} ms")
        lines.append("")
        
        # Site统计表头
        site_headers = ['All'] + [k for k in site_stats.keys() if k != 'All']
        header_line = f"Site NO:                    {'All':<16}"
        for site_key in site_headers[1:]:
            header_line += f" {site_key:<16}"
        lines.append(header_line)
        
        # Total QTY
        total_line = f"Total QTY:                 {site_stats['All']['TOTAL']:>5}"
        for site_key in site_headers[1:]:
            total_line += f"          {site_stats[site_key]['TOTAL']:>5}"
        lines.append(total_line)
        
        # Pass QTY
        pass_line = f"Pass QTY:          {site_stats['All']['PASS']:>5}|{site_stats['All']['PASS_RATE']:>6.2f}%"
        for site_key in site_headers[1:]:
            pass_line += f"   {site_stats[site_key]['PASS']:>5}|{site_stats[site_key]['PASS_RATE']:>6.2f}%"
        lines.append(pass_line)
        
        # Fail QTY
        fail_line = f"Fail QTY:          {site_stats['All']['FAIL']:>5}|{site_stats['All']['FAIL_RATE']:>6.2f}%"
        for site_key in site_headers[1:]:
            fail_line += f"   {site_stats[site_key]['FAIL']:>5}|{site_stats[site_key]['FAIL_RATE']:>6.2f}%"
        lines.append(fail_line)
        
        # Abort/Null (暂时设为0)
        abort_line = f"Abort QTY:            0|  0.00%"
        for _ in site_headers[1:]:
            abort_line += f"      0|  0.00%"
        lines.append(abort_line)
        
        null_line = f"Null QTY:             0|  0.00%"
        for _ in site_headers[1:]:
            null_line += f"      0|  0.00%"
        lines.append(null_line)
        lines.append("")
        
        # Fresh/Retest统计
        fresh_line = f"Fresh QTY:         {retest_stats['FRESH']:>5}|{retest_stats['FRESH_RATE']:>6.2f}%"
        for site_key in site_headers[1:]:
            # 这里简化处理，实际应该按site分别统计
            fresh_line += f"   {retest_stats['FRESH']:>5}|{retest_stats['FRESH_RATE']:>6.2f}%"
        lines.append(fresh_line)
        
        retest_line = f"Retest QTY:        {retest_stats['RETEST']:>5}|{retest_stats['RETEST_RATE']:>6.2f}%"
        for site_key in site_headers[1:]:
            retest_line += f"   {retest_stats['RETEST']:>5}|{retest_stats['RETEST_RATE']:>6.2f}%"
        lines.append(retest_line)
        lines.append("")
        
        # ==================== Soft Bin Statistic ====================
        soft_bin_stats = SummaryGenerator.calculate_bin_statistics(df_module.prr_df, 'SOFT_BIN')
        
        lines.append("Soft Bin Statistic")
        lines.append(f"BIN:   Bin Name                       {'All':<16}")
        for site_key in site_headers[1:]:
            lines[-1] += f" {site_key.split('(')[0]:<14}"
        
        for bin_stat in soft_bin_stats:
            bin_line = f"{bin_stat['BIN']:<6} {bin_stat['BIN_TYPE']}:{bin_stat['BIN_NAME']:<20}"
            bin_line += f"{bin_stat['QTY']:>5}|{bin_stat['PERCENTAGE']:>6.2f}%"
            # 按site分别统计
            site_bin_stats = bin_stat.get('SITE_STATS', {})
            for site_key in site_headers[1:]:
                # 使用保存的整数编号进行匹配
                site_num_int = site_stats[site_key].get('SITE_NUM_INT')
                if site_num_int and site_num_int in site_bin_stats:
                    bin_line += f"   {site_bin_stats[site_num_int]['QTY']:>5}|{site_bin_stats[site_num_int]['PERCENTAGE']:>6.2f}%"
                else:
                    bin_line += f"      0|  0.00%"
            lines.append(bin_line)
        lines.append("")

        # ==================== Hard Bin Statistic ====================
        hard_bin_stats = SummaryGenerator.calculate_bin_statistics(df_module.prr_df, 'HARD_BIN')

        lines.append("Hard Bin Statistic")
        lines.append(f"BIN:   Bin Name                       {'All':<16}")
        for site_key in site_headers[1:]:
            lines[-1] += f" {site_key.split('(')[0]:<14}"

        for bin_stat in hard_bin_stats:
            bin_line = f"{bin_stat['BIN']:<6} {bin_stat['BIN_TYPE']}:{bin_stat['BIN_NAME']:<20}"
            bin_line += f"{bin_stat['QTY']:>5}|{bin_stat['PERCENTAGE']:>6.2f}%"
            # 按site分别统计
            site_bin_stats = bin_stat.get('SITE_STATS', {})
            for site_key in site_headers[1:]:
                # 使用保存的整数编号进行匹配
                site_num_int = site_stats[site_key].get('SITE_NUM_INT')
                if site_num_int and site_num_int in site_bin_stats:
                    bin_line += f"   {site_bin_stats[site_num_int]['QTY']:>5}|{site_bin_stats[site_num_int]['PERCENTAGE']:>6.2f}%"
                else:
                    bin_line += f"      0|  0.00%"
            lines.append(bin_line)
        lines.append("")
        
        return "\n".join(lines)

