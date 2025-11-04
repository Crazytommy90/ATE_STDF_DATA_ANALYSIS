"""
-*- coding: utf-8 -*-
@Author  : Link
@Time    : 2022/12/20 14:15
@Site    : 
@File    : capability.py
@Software: PyCharm
@Remark  : 
"""
from typing import List, Union

import pandas as pd
import numpy as np

from app_test.test_utils.wrapper_utils import Time
from common.app_variable import PtmdModule, LimitType, DataModule, DatatType, Calculation, FailFlag
from parser_core.stdf_parser_func import PtmdOptFlag, DtpTestFlag, PtmdParmFlag


class CapabilityUtils:

    @staticmethod
    def calculate_cp(hi_limit: float, lo_limit: float, data_std: float) -> float:
        """
        计算 Cp (Process Capability Index)
        Cp = (USL - LSL) / (6σ)

        :param hi_limit: 上限 (USL)
        :param lo_limit: 下限 (LSL)
        :param data_std: 样本标准差
        :return: Cp值
        """
        if data_std == 0:
            return np.nan
        return round((hi_limit - lo_limit) / (6 * data_std), 6)

    @staticmethod
    def calculate_pp_ppk(data_mean: float, hi_limit: float, lo_limit: float,
                         data_std_total: float, has_low_limit: bool, has_high_limit: bool) -> tuple:
        """
        计算 Pp 和 Ppk (Process Performance Index)
        Pp = (USL - LSL) / (6σ_total)
        Ppk = min(Ppu, Ppl)
        Ppu = (USL - μ) / (3σ_total)
        Ppl = (μ - LSL) / (3σ_total)

        :param data_mean: 数据均值
        :param hi_limit: 上限 (USL)
        :param lo_limit: 下限 (LSL)
        :param data_std_total: 总体标准差
        :param has_low_limit: 是否有下限
        :param has_high_limit: 是否有上限
        :return: (Pp, Ppk)
        """
        if data_std_total == 0:
            return np.nan, np.nan

        # 计算 Pp
        if has_low_limit and has_high_limit:
            pp = (hi_limit - lo_limit) / (6 * data_std_total)
        else:
            pp = np.nan

        # 计算 Ppk
        ppk_values = []
        if has_high_limit:
            ppu = (hi_limit - data_mean) / (3 * data_std_total)
            ppk_values.append(ppu)
        if has_low_limit:
            ppl = (data_mean - lo_limit) / (3 * data_std_total)
            ppk_values.append(ppl)

        if ppk_values:
            ppk = min(ppk_values)
        else:
            ppk = np.nan

        return round(pp, 6) if not np.isnan(pp) else np.nan, round(abs(ppk), 6) if not np.isnan(ppk) else np.nan

    @staticmethod
    def calculate_sigma_level(cpk: float) -> float:
        """
        计算 Sigma Level (西格玛水平)
        Sigma Level ≈ Cpk × 3 + 1.5

        :param cpk: Cpk值
        :return: Sigma Level
        """
        if np.isnan(cpk) or cpk <= 0:
            return np.nan
        # 简化公式：Sigma Level = Cpk * 3 + 1.5
        # 更精确的计算需要查表或使用正态分布函数
        sigma_level = cpk * 3 + 1.5
        return round(sigma_level, 2)

    @staticmethod
    # @Time()
    def top_fail(top_fail_df: pd.DataFrame, data_df: pd.DataFrame) -> (pd.DataFrame, int):
        """
        TODO:
            从原始数据集中计算, 直接确认是否fail
            不能找PASS, 要找Fail了多少
            时间开销大
        :param top_fail_df: ["PART_ID", "FAIL_FLAG"]
        :param data_df: Dtp Data, 需要和 top_fail_df 同步
        :return: 60k row, 40 column, 800ms, column吃时间
        """
        all_qty = len(top_fail_df)
        temp_data_df = data_df[data_df.index.isin(top_fail_df.index)]
        fail_df = temp_data_df[temp_data_df.FAIL_FLG == FailFlag.FAIL]
        fail_qty = len(fail_df)
        top_fail_df = top_fail_df[~top_fail_df.index.isin(fail_df.index)]
        if len(top_fail_df) > all_qty:
            raise Exception("error len(top_fail_df) > all_qty")
        return top_fail_df, fail_qty

    @staticmethod
    @Time()
    def calculation_top_fail(df_module: DataModule):
        """
        Top Fail如何计算? 算逐项fail即可.
        TODO:
            1. 去除多个文件中, 重复的数据
            2. 取数据并进行运算
        :param df_module:
        :return:
        """
        df_use_top_fail = df_module.prr_df
        dtp_df = df_module.dtp_df
        top_fail_dict = {}
        for row in df_module.ptmd_df.itertuples():  # type:PtmdModule
            " 逐项计算Top Fail "
            df_use_top_fail, fail_qty = CapabilityUtils.top_fail(
                df_use_top_fail,
                dtp_df.loc[row.TEST_ID]
            )
            try:
                top_fail_dict[row.TEST_ID] += fail_qty
            except:
                top_fail_dict[row.TEST_ID] = fail_qty
        return top_fail_dict

    @staticmethod
    # @Time()
    def re_cal_top_fail(ptmd: PtmdModule, top_fail_df: pd.DataFrame, data_df: pd.DataFrame):
        """
        重新计算, 使用ptmd中包含的新的limit信息
        :param ptmd:
        :param top_fail_df:
        :param data_df:
        :return: 60k row, 40 column, 800ms -> ??? sometimes faster than top_fail function
        """
        all_qty = len(top_fail_df)
        logic_and = []
        data_df = data_df[data_df.index.isin(top_fail_df.index)]
        if not ptmd.OPT_FLAG & PtmdOptFlag.NoLowLimit:
            if ptmd.PARM_FLG & PtmdParmFlag.EqualLowLimit:  # >=
                logic_and.append((data_df.RESULT >= ptmd.LO_LIMIT))
            else:  # >
                logic_and.append((data_df.RESULT > ptmd.LO_LIMIT))
        if not ptmd.OPT_FLAG & PtmdOptFlag.NoHighLimit:
            if ptmd.PARM_FLG & PtmdParmFlag.EqualHighLimit:  # <=
                logic_and.append((data_df.RESULT <= ptmd.HI_LIMIT))
            else:  # <
                logic_and.append((data_df.RESULT < ptmd.HI_LIMIT))
        if len(logic_and) == 0:  # No fail
            return top_fail_df, 0
        if len(logic_and) == 1:
            items = logic_and[0]
            fail_df = data_df.loc[~items]
        else:
            items = np.logical_and(*logic_and)
            fail_df = data_df.loc[~items]
        fail_qty = len(fail_df)
        top_fail_df = top_fail_df[~top_fail_df.index.isin(fail_df.index)]
        if len(top_fail_df) > all_qty:
            raise Exception("error len(top_fail_df) > all_qty")
        return top_fail_df, fail_qty

    @staticmethod
    @Time()
    def calculation_new_top_fail(df_module: DataModule):
        """
        重新设置limit值后top fail的计算 -> 精度丢失问题, 即使limit没有变化, 算出来的fail rate和上面的函数可能也不一样
        运行时间肯定会长了一些 -> 实际和上面的操作时间一致? 上面的操作应该会更加简单和速度的.
        Top Fail如何计算? 算逐项fail即可.
        :param df_module:
        :return:
        """
        df_use_top_fail = df_module.prr_df
        dtp_df = df_module.dtp_df

        top_fail_dict = {}
        for row in df_module.ptmd_df.itertuples():  # type:PtmdModule
            " 逐项计算Top Fail + 根据dict中的limit重新计算 "
            df_use_top_fail, fail_qty = CapabilityUtils.re_cal_top_fail(
                row,
                df_use_top_fail,
                dtp_df.loc[row.TEST_ID]
            )
            try:
                top_fail_dict[row.TEST_ID] += fail_qty
            except:
                top_fail_dict[row.TEST_ID] = fail_qty
        return top_fail_dict

    @staticmethod
    def calculation_ptr(ptmd: PtmdModule, top_fail_qty: int, data_df: pd.DataFrame) -> Union[Calculation, dict]:
        """
        TODO:
            3倍中位数绝对偏差去极值
            时间开销大
        :param top_fail_qty:
        :param ptmd:
        :param data_df:
        :return:
        """

        # def _mad(factor):
        #     """
        #     3倍中位数绝对偏差去极值 by CSDN: https://blog.csdn.net/m0_37967652/article/details/122900866
        #     """
        #     me = np.median(factor)
        #     mad = np.median(abs(factor - me))
        #     # 求出3倍中位数的上下限制
        #     up = me + (3 * 1.4826 * mad)
        #     down = me - (3 * 1.4826 * mad)
        #     # 利用3倍中位数的值去极值
        #     factor = np.where(factor > up, up, factor)
        #     factor = np.where(factor < down, down, factor)
        #     return factor

        # data_df["RESULT"] = _mad(data_df["RESULT"])
        fail_exec = data_df.FAIL_FLG == FailFlag.FAIL
        reject_qty = len(data_df[fail_exec])
        pass_df = data_df[~fail_exec]
        data_mean, data_min, data_max, data_std, data_median = \
            pass_df.RESULT.mean(), pass_df.RESULT.min(), pass_df.RESULT.max(), pass_df.RESULT.std(), \
            pass_df.RESULT.median()

        # 处理零标准差
        if data_std == 0:
            data_std = 1E-05

        # 检查是否有上下限
        has_low_limit = not (ptmd.OPT_FLAG & PtmdOptFlag.NoLowLimit)
        has_high_limit = not (ptmd.OPT_FLAG & PtmdOptFlag.NoHighLimit)

        # 计算 Cpk
        cpk_values = []
        if has_high_limit:
            cpu = (ptmd.HI_LIMIT - data_mean) / (3 * data_std)
            cpk_values.append(cpu)
        if has_low_limit:
            cpl = (data_mean - ptmd.LO_LIMIT) / (3 * data_std)
            cpk_values.append(cpl)

        if cpk_values:
            cpk = round(min(cpk_values), 6)
        else:
            cpk = np.nan

        # 计算 Cp (只有双边限制时才计算)
        if has_low_limit and has_high_limit:
            cp = CapabilityUtils.calculate_cp(ptmd.HI_LIMIT, ptmd.LO_LIMIT, data_std)
        else:
            cp = np.nan

        # 计算 Pp 和 Ppk (使用总体标准差)
        data_std_total = pass_df.RESULT.std(ddof=0)  # ddof=0 表示总体标准差
        if data_std_total == 0:
            data_std_total = 1E-05
        pp, ppk = CapabilityUtils.calculate_pp_ppk(
            data_mean, ptmd.HI_LIMIT, ptmd.LO_LIMIT,
            data_std_total, has_low_limit, has_high_limit
        )

        # 计算 Sigma Level
        sigma_level = CapabilityUtils.calculate_sigma_level(abs(cpk) if not np.isnan(cpk) else np.nan)

        # Limit类型
        l_limit_type = LimitType.ThenLowLimit
        if ptmd.OPT_FLAG & PtmdOptFlag.NoLowLimit:
            l_limit_type = LimitType.NoLowLimit
        if ptmd.PARM_FLG & PtmdParmFlag.EqualLowLimit:
            l_limit_type = LimitType.EqualLowLimit
        h_limit_type = LimitType.ThenHighLimit
        if ptmd.OPT_FLAG & PtmdOptFlag.NoHighLimit:
            h_limit_type = LimitType.NoHighLimit
        if ptmd.PARM_FLG & PtmdParmFlag.EqualHighLimit:
            h_limit_type = LimitType.EqualHighLimit
        temp_dict = {
            "TEST_ID": ptmd.TEST_ID,  # 每个测试项目最后整合后只会有唯一一个TEST_ID
            "TEST_TYPE": ptmd.DATAT_TYPE,
            "TEST_NUM": ptmd.TEST_NUM,
            "TEST_TXT": ptmd.TEST_TXT,
            "UNITS": ptmd.UNITS,
            "LO_LIMIT": ptmd.LO_LIMIT,  # 保持原始limit值，不进行四舍五入
            "HI_LIMIT": ptmd.HI_LIMIT,  # 保持原始limit值，不进行四舍五入
            "AVG": round(data_mean, 6),
            "STD": round(data_std, 6),
            "MEDIAN": round(data_median, 6),
            # 制程能力指标
            "CPK": abs(cpk) if not np.isnan(cpk) else np.nan,
            "CP": cp,
            "PPK": ppk,
            "PP": pp,
            "SIGMA_LEVEL": sigma_level,
            # 数量统计
            "QTY": len(data_df),
            "FAIL_QTY": top_fail_qty,
            # TODO: 注意 top fail的Rate一定是要%总颗数,不能%测试颗数, 待更新
            "FAIL_RATE": "{}%".format(round(top_fail_qty / len(data_df) * 100, 3)),
            "REJECT_QTY": reject_qty,
            "REJECT_RATE": "{}%".format(round(reject_qty / len(data_df) * 100, 3)),
            "MIN": round(data_min, 6),  # 注意, 是取得PASS区域的数据
            "MAX": round(data_max, 6),  # 注意, 是取得PASS区域的数据
            "LO_LIMIT_TYPE": l_limit_type,
            "HI_LIMIT_TYPE": h_limit_type,
            "ALL_DATA_MIN": round(data_df.RESULT.min(), 6),
            "ALL_DATA_MAX": round(data_df.RESULT.max(), 6),
            "TEXT": ptmd.TEXT,
        }
        # return Calculation(**temp_dict)
        return temp_dict

    @staticmethod
    def calculation_ftr(ptmd: PtmdModule, top_fail_qty: int, data_df: pd.DataFrame) -> Union[Calculation, dict]:
        """
        只计算fail rate
        :param top_fail_qty:
        :param ptmd:
        :param data_df:
        :return:
        """
        reject_qty = len(data_df[data_df.TEST_FLG & DtpTestFlag.TestFailed == DtpTestFlag.TestFailed])
        temp_dict = {
            "TEST_ID": ptmd.TEST_ID,  # 每个测试项目最后整合后只会有唯一一个TEST_ID
            "TEST_TYPE": ptmd.DATAT_TYPE,
            "TEST_NUM": ptmd.TEST_NUM,
            "TEST_TXT": ptmd.TEST_TXT,
            "UNITS": ptmd.UNITS,
            "LO_LIMIT": ptmd.LO_LIMIT,  # 保持原始limit值，不进行四舍五入
            "HI_LIMIT": ptmd.HI_LIMIT,  # 保持原始limit值，不进行四舍五入
            "AVG": np.nan,
            "STD": np.nan,
            "CPK": np.nan,
            "QTY": len(data_df),
            "FAIL_QTY": top_fail_qty,
            # TODO: 注意 top fail的Rate一定是要%总颗数,不能%测试颗数, 待更新
            "FAIL_RATE": "{}%".format(round(top_fail_qty / len(data_df) * 100, 3)),
            "REJECT_QTY": reject_qty,
            "REJECT_RATE": "{}%".format(round(reject_qty / len(data_df) * 100, 3)),
            "MIN": -0.1,  # 注意, 是取得有效区域的数据
            "MAX": 1.1,  # 注意, 是取得有效区域的数据
            "LO_LIMIT_TYPE": LimitType.ThenLowLimit,
            "HI_LIMIT_TYPE": LimitType.EqualHighLimit,
            "ALL_DATA_MIN": -0.1,
            "ALL_DATA_MAX": 1.1,
            "TEXT": ptmd.TEXT,
        }
        # return Calculation(**temp_dict)
        return temp_dict

    @staticmethod
    @Time()
    def calculation_capability(df_module: DataModule, top_fail_dict: dict) -> List[dict]:
        """
        python dict 是可以保持顺序的
            用于计算整个数据的Top Fail等信息
        :param df_module:
        :param top_fail_dict:
        :return:
        """
        capability_key_list = []
        for row in df_module.ptmd_df.itertuples():  # type:PtmdModule
            data_df = df_module.dtp_df.loc[row.TEST_ID].loc[:].copy()  # TODO: 10%时间开销
            if row.DATAT_TYPE in {DatatType.PTR, DatatType.MPR}:
                cal_data = CapabilityUtils.calculation_ptr(
                    row, top_fail_dict[row.TEST_ID], data_df
                )
                capability_key_list.append(cal_data)
                continue
            if row.DATAT_TYPE == DatatType.FTR:
                cal_data = CapabilityUtils.calculation_ftr(
                    row, top_fail_dict[row.TEST_ID], data_df
                )
                capability_key_list.append(cal_data)
                continue
        return capability_key_list
