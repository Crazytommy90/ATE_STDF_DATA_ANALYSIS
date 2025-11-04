"""
-*- coding: utf-8 -*-
@Author  : Link
@Time    : 2021/12/13 20:20
@Software: PyCharm
@File    : stdf_parser.py
@Remark  : 
"""
import os

from Semi_ATE import STDF
from common.app_variable import GlobalVariable


class SemiStdfUtils:
    @staticmethod
    def is_std(file_name):
        suffix = os.path.splitext(file_name)[-1]
        if suffix not in GlobalVariable.STD_SUFFIXES:
            return False
        return True

    @staticmethod
    def get_lot_info_by_semi_ate(filepath: str, **kwargs) -> dict:
        """
        获取STDF文件的LOT信息和Summary所需的静态信息
        优化：一次性读取所有静态信息，避免后续重复读取STDF文件
        :param filepath: STDF文件路径
        :param kwargs: 额外参数（如FILE_NAME, ID等）
        :return: 包含LOT信息和Summary静态信息的字典
        """
        data_dict = {
            "FILE_PATH": filepath,
            **kwargs,
            # MIR - 基本信息
            "LOT_ID": "",
            "SBLOT_ID": "",
            "WAFER_ID": "",
            "BLUE_FILM_ID": "",
            'TEST_COD': '',
            'FLOW_ID': '',
            'PART_TYP': '',
            'JOB_NAM': '',
            'TST_TEMP': 0,
            'NODE_NAM': '',
            'SETUP_T': 0,
            'START_T': 0,
            'SITE_CNT': 0,
            # MIR - Summary静态信息（不受limit影响）
            'STAT_NUM': 0,
            'MODE_COD': '',
            'BURN_TIM': 0,
            'OPER_NAM': '',
            'EXEC_TYP': '',
            'EXEC_VER': '',
            'USER_TXT': '',
            'PKG_TYP': '',
            'FAMLY_ID': '',
            'DATE_COD': '',
            'FACIL_ID': '',
            'FLOOR_ID': '',
            'PROC_ID': '',
            # MRR - 完成信息
            'FINISH_T': 0,
            'DISP_COD': '',
            'USR_DESC': '',
            'EXC_DESC': '',
        }

        if "DEMO" in filepath:
            data_dict["LOT_ID"] = "DEMO_LOT"
            data_dict["SBLOT_ID"] = "DEMO_SB"
            data_dict["WAFER_ID"] = "DEMO_WAFER"
            data_dict["TEST_COD"] = "CP1"
            data_dict["FLOW_ID"] = "R0"
            return data_dict

        # 一次性读取所有需要的记录
        for REC in STDF.records_from_file(filepath):
            if REC is None:
                continue

            # PIR出现表示测试数据开始，之前的记录已读取完毕
            if REC.id == "PIR":
                break

            # MIR - Master Information Record（主信息记录）
            if REC.id == "MIR":
                mir = REC.to_dict()
                # 基本信息
                data_dict["LOT_ID"] = mir.get("LOT_ID", "")
                data_dict["SBLOT_ID"] = mir.get("SBLOT_ID", "")
                data_dict["TEST_COD"] = mir.get("TEST_COD", "")
                data_dict["FLOW_ID"] = mir.get("FLOW_ID", "")
                data_dict["PART_TYP"] = mir.get("PART_TYP", "")
                data_dict["JOB_NAM"] = mir.get("JOB_NAM", "")
                data_dict["TST_TEMP"] = mir.get("TST_TEMP", 0)
                data_dict["NODE_NAM"] = mir.get("NODE_NAM", "")
                data_dict["SETUP_T"] = mir.get("SETUP_T", 0)
                data_dict["START_T"] = mir.get("START_T", 0)
                # Summary静态信息（不受limit影响）
                data_dict["STAT_NUM"] = mir.get("STAT_NUM", 0)
                data_dict["MODE_COD"] = mir.get("MODE_COD", "")
                data_dict["BURN_TIM"] = mir.get("BURN_TIM", 0)
                data_dict["OPER_NAM"] = mir.get("OPER_NAM", "")
                data_dict["EXEC_TYP"] = mir.get("EXEC_TYP", "")
                data_dict["EXEC_VER"] = mir.get("EXEC_VER", "")
                data_dict["USER_TXT"] = mir.get("USER_TXT", "")
                data_dict["PKG_TYP"] = mir.get("PKG_TYP", "")
                data_dict["FAMLY_ID"] = mir.get("FAMLY_ID", "")
                data_dict["DATE_COD"] = mir.get("DATE_COD", "")
                data_dict["FACIL_ID"] = mir.get("FACIL_ID", "")
                data_dict["FLOOR_ID"] = mir.get("FLOOR_ID", "")
                data_dict["PROC_ID"] = mir.get("PROC_ID", "")

            # WIR - Wafer Information Record（晶圆信息记录）
            elif REC.id == "WIR":
                wir = REC.to_dict()
                if wir.get("HEAD_NUM") == 233:
                    data_dict["BLUE_FILM_ID"] = wir.get("WAFER_ID", "")
                else:
                    data_dict["WAFER_ID"] = wir.get("WAFER_ID", "")

            # SDR - Site Description Record（测试站点描述记录）
            elif REC.id == "SDR":
                sdr = REC.to_dict()
                data_dict["SITE_CNT"] = sdr.get("SITE_CNT", 0)

            # MRR - Master Results Record（主结果记录）
            elif REC.id == "MRR":
                mrr = REC.to_dict()
                data_dict["FINISH_T"] = mrr.get("FINISH_T", 0)
                data_dict["DISP_COD"] = mrr.get("DISP_COD", "")
                data_dict["USR_DESC"] = mrr.get("USR_DESC", "")
                data_dict["EXC_DESC"] = mrr.get("EXC_DESC", "")

        return data_dict
