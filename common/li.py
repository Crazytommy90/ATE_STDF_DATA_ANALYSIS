#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : li.py
@Author  : Link
@Time    : 2022/12/23 20:35
@Mark    : 
"""

from multiprocessing import Process
from typing import List, Dict, Union, Tuple

import pandas as pd
from PySide2.QtCore import QObject, Signal

from app_test.test_utils.wrapper_utils import Time
from common.app_variable import DataModule, ToChartCsv, GlobalVariable
from common.cal_interface.capability import CapabilityUtils
from parser_core.stdf_parser_file_write_read import ParserData
from report_core.openxl_utils.utils import OpenXl


class SummaryCore:
    """
    1. 每个文件解析完成后, 会有各个Summary和子数据
    2. Summary会经过组合后生成 SummaryDf
        SummaryDf -> by start_time 排序
        | ID  | R | LOT_ID | SB_LOT_ID | FLOW_ID | QTY | PASS | YIELD | PASS_VERIFY | ... |
        | ··· | Y | ······ |
        | ··· | N |
        | ···

        df_dict ->
        {
            逻辑需要优化, 数据要在需要的时候才从HDF5中读取·
        }
    3. 组合新的Limit数据,注意测试项目和TEST_ID的对应即可
    4. SummaryDf 展示在Tree上
        Group By: LOT_ID -> FLOW_ID ? -> SB_LOT_ID ?
            groupby之后 使用min(START_TIME), max(FINISH_TIME), sum(QTY), sum(PASS)
        给到Tree的数据:
            [
                {
                | ID  | LOT_ID | ...
                children:
                    [ {
                    | ID  | LOT_ID | ...
                    }, ... ]
                },
                {
                | ID  | LOT_ID | ...
                children:
                    [ {
                    | ID  | LOT_ID | ...
                    }, ... ]
                }
            ]
    5. 从Tree中拿到IDS, 汇整为NowSummaryDf, 并拿到Group信息后汇整为 GROUP列
        会有两份数据, 1. NowSummaryDf 2. NowDfs->将df_dict中的数据按需求contact起来
    6. 支持多个window来汇整数据
    """
    ready: bool = False
    summary_df: pd.DataFrame = None

    def set_data(self, summary: Union[list, pd.DataFrame]):
        """
        后台必然默认传送一个元组, 拆包为三份数据,并且传来的summary_df已经经过排序
        而且这个返回的数据是比较重要的!!!@后期是需要用在服务器缓存中的
        """
        if summary is None or (isinstance(summary, (list, pd.DataFrame)) and len(summary) == 0):
            return
        if isinstance(summary, list):
            self.summary_df = pd.DataFrame(summary)
        else:
            self.summary_df = summary
        self.ready = True
        return self.ready

    def get_summary_tree(self):
        """
        SummaryDf 展示在Tree上
        :return:
        """
        tree_dict_list = list()
        for key, e_df in self.summary_df.groupby("LOT_ID"):  # type:str, pd.DataFrame
            key = str(key)
            qty = e_df["QTY"].sum()
            pass_qty = e_df["PASS"].sum()
            if qty == 0:
                pass_yield = "0.0%"
            else:
                pass_yield = '{}%'.format(round(pass_qty / qty * 100, 2))
            tree_dict = {
                "LOT_ID": key,
                "QTY": qty,
                "PASS": pass_qty,
                "YIELD": pass_yield,
                "START_T": e_df["START_T"].min(),
                "children": e_df.to_dict(orient="records")
            }
            tree_dict_list.append(tree_dict)

        return tree_dict_list

    def add_custom_node(self, ids: List[int], new_lot_id: str):
        """
        将多个数据组合为一个自定义的LOT, 比如两个版本的数据对比, 将一部分分为版本A(LOT_A), 另一部分分为版本B(LOT_B)
        其实没那么复杂, 不需要新建各种五花八门的数据, 就直接把旧的列的LOT_ID改名即可
        {
            'FILE_PATH': '',
            'FILE_NAME': '',
            'ID': 100000,
            'LOT_ID': '',
            'SBLOT_ID': '',
            "WAFER_ID": "",
            "BLUE_FILM_ID": "",
            'TEST_COD': '',
            'FLOW_ID': '',
            'PART_TYP': '',
            'JOB_NAM': '',
            'TST_TEMP': '',
            'NODE_NAM': '',
            'SETUP_T': 1620734064,
            'START_T': 1620734070,
            'SITE_CNT': 1,
            'QTY': 2534,
            'PASS': 2534,
            'YIELD': '100.0%',
            'PART_FLAG': 0,
            'READ_FAIL': True
            'HDF5_PATH': ""
            },
        """
        if self.summary_df is None:
            return
        self.summary_df.loc[self.summary_df.ID.isin(ids), "LOT_ID"] = new_lot_id

    def load_select_data(self, ids: List[int], quick: bool = False, sample_num: int = 1E4):
        """
        返回数据
        整理出一个比较完整的 ptmd 的整合dict
        重复的ptmd_dict就选用最新的
        主要给每个单元的Prr给一个ID用于数据链接
        TODO: 不在一个summary中指向多个文件位置
        :param ids:
        :param quick:
        :param sample_num:
        :return:
        """
        id_module_dict = {}
        select_summary = self.summary_df[self.summary_df.ID.isin(ids)]
        for select in select_summary.itertuples():
            ID = getattr(select, "ID")
            data_module = ParserData.load_hdf5_analysis(
                getattr(select, "HDF5_PATH"),
                int(getattr(select, "PART_FLAG")),
                int(getattr(select, "READ_FAIL")),
                unit_id=ID,
            )
            id_module_dict[ID] = data_module
        return select_summary, id_module_dict

    # def get_bin_summary(self, ids: List[int], group_params: Union[list, None], da_group_params: Union[list, None]):
    #     """
    #     bin和bin_map这类数据是不需要完全载入详细数据集参数的, 所以数据临时即可取得
    #     :param da_group_params: 根据Site或是Head(不考虑)的分组
    #     :param group_params: 根据Summary的分组
    #     :param ids:
    #     :return: 返回可以直接被Plot的数据
    #     """


class Li(QObject):
    """
    从Tree中得到的确定是需要的数据.
    进到这里面的数据都是数据帧和控制Group的Summary
    """
    select_summary: pd.DataFrame = None
    id_module_dict: Dict[int, DataModule] = None
    df_module: DataModule = None
    # ======================== signal
    QCalculation = Signal()  # capability_key_list 改变的信号
    QMessage = Signal(str)  # 用于全局来调用一个MessageBox, 只做提示
    QStatusMessage = Signal(str)  # 用于全局来调用一个MessageBox, 只做提示

    QChartSelect = Signal()  # 用于刷新选取的数据
    QChartRefresh = Signal()  # 用于重新刷新所有的图
    # ======================== Temp
    capability_key_list: list = None
    capability_key_dict: Dict[int, dict] = None  # key: TEST_ID -> 仅仅用于Show Plot
    top_fail_dict: dict = None

    # ======================== 用于绘图或是capability group
    to_chart_csv_data: ToChartCsv = None
    group_params = None
    da_group_params = None

    # ======================== 新增：操作状态管理
    _original_df_module: DataModule = None  # 保存原始数据
    _current_limit_changes: Dict[int, Tuple[float, float, str, str]] = None  # 当前limit变更
    _operation_state: str = None  # 操作状态: None, 'limit_changed', 'data_filtered'

    def __init__(self):
        super(Li, self).__init__()

    def set_data(self,
                 select_summary: pd.DataFrame,
                 id_module_dict: Dict[int, DataModule]
                 ):
        """

        :param select_summary: Mir&Wir等相关的信息整合的Summary
        :param id_module_dict: 每行Summary都有一个唯一ID, 指向了module数据
        :return:
        """
        self.select_summary = select_summary.copy()
        self.select_summary["GROUP"] = "*"
        self.id_module_dict = id_module_dict

    def concat(self):
        """
        TODO:
            prr_df.set_index(["PART_ID"])
            dtp_df.set_index(["TEST_ID", "PART_ID"])
            dtp_df.TEST_ID <==> dtp_df.TEST_ID
            prr_df.ID <==> select_summary.ID
        active:
            1. 整合进入数据空间的数据, 都contact成一个数据, 关注["ID", "PART_ID"]这两列
            2. 最终concat成为一份数据, 再做计算就清晰多了
        :return:
        """
        if len(self.id_module_dict) == 0:
            return
        data_module_list = []
        for df_id, module in self.id_module_dict.items():
            data_module_list.append(module)
        self.df_module = ParserData.contact_data_module(data_module_list)
        self.df_module.prr_df.set_index(["DIE_ID"], inplace=True)
        self.df_module.dtp_df.set_index(["TEST_ID", "DIE_ID"], inplace=True)
        self.df_module.prr_df["DA_GROUP"] = "*"

    def calculation_top_fail(self):
        """
        1. 计算top fail
        2. 需要在unstack的数据格式上
        3. 根据选取的数据来做计算
        :return:
        """
        self.top_fail_dict = CapabilityUtils.calculation_top_fail(self.df_module)

    def calculation_capability(self):
        """
        1. 计算reject rate
        2. 计算cpk等
        :return:
        """
        self.capability_key_list = CapabilityUtils.calculation_capability(self.df_module, self.top_fail_dict)
        if self.capability_key_dict is None:
            self.capability_key_dict = dict()
        else:
            self.capability_key_dict.clear()
        for each in self.capability_key_list:
            self.capability_key_dict[each["TEST_ID"]] = each

    @Time()
    def background_generation_data_use_to_chart_and_to_save_csv(self):
        """
        将数据叠起来, 用于数据可视化和导出到JMP和Altair
        TODO: 数据叠加起来的时候, 会做一个去最后出现的重复项目的操作
        :return:
        """
        if self.to_chart_csv_data is None:
            self.to_chart_csv_data = ToChartCsv()
        temp_result = self.df_module.dtp_df[["RESULT"]]
        temp_result = temp_result[~temp_result.index.duplicated(keep="last")]
        temp_result = temp_result.unstack(0).RESULT
        self.to_chart_csv_data.df = temp_result

    def background_generation_limit_data_use_to_pat(self):
        """
        用于PAT
        需要提示建议不能在多LOT的Group条件下操作
        :return:
        """
        temp_result = self.df_module.dtp_df[["LO_LIMIT", "HI_LIMIT"]].copy()
        temp_result = temp_result[~temp_result.index.duplicated(keep="last")]
        self.to_chart_csv_data.limit = temp_result.unstack(0)

    def set_chart_data(self, chart_df: Union[pd.DataFrame, None]):
        """
        用于pyqtgraph绘图
        :param chart_df:
        :return:
        """
        self.to_chart_csv_data.chart_df = chart_df
        if chart_df is None:
            self.select_chart()
            return
        group_data = {}
        for (group, da_group), df in self.to_chart_csv_data.chart_df.groupby(["GROUP", "DA_GROUP"]):
            key = f"{group}@{da_group}"
            group_data[key] = df
        self.to_chart_csv_data.group_chart_df = group_data
        self.select_chart()

    def set_data_group(self, group_params: Union[list, None], da_group_params: Union[list, None]):
        """
        专注将数据分组
        :param group_params:
        :param da_group_params:
        :return:
        """
        if self.select_summary is None:
            return
        if self.df_module is None or self.df_module.prr_df is None:
            return
        self.group_params, self.da_group_params = group_params, da_group_params
        if group_params is None:
            temp_column_data = '*'
        else:
            temp_column_data = None
            for index, each in enumerate(group_params):
                if index == 0:
                    temp_column_data = self.select_summary[each].astype(str)
                else:
                    temp_column_data = temp_column_data + "|" + self.select_summary[each].astype(str)

        self.select_summary.loc[:, "GROUP"] = temp_column_data
        if da_group_params is None:
            temp_column_data = '*'
        else:
            temp_column_data = None
            for index, each in enumerate(da_group_params):
                if index == 0:
                    temp_column_data = self.df_module.prr_df[each].astype(str)
                else:
                    temp_column_data = temp_column_data + "|" + self.df_module.prr_df[each].astype(str)
        self.df_module.prr_df.loc[:, "DA_GROUP"] = temp_column_data

        self.background_generation_data_use_to_chart_and_to_save_csv()
        data = pd.merge(self.to_chart_csv_data.df, self.df_module.prr_df, left_index=True, right_index=True)
        self.to_chart_csv_data.df = pd.merge(
            data, self.select_summary[["ID", "GROUP"]], on="ID"
        )

        group_data = {}
        for (group, da_group), df in self.to_chart_csv_data.df.groupby(["GROUP", "DA_GROUP"]):
            key = f"{group}@{da_group}"
            group_data[key] = df
        self.to_chart_csv_data.group_df = group_data
        self.set_chart_data(None)
        self.refresh_chart()
        return True

    def get_unstack_data_to_csv_or_jmp_or_altair(self, test_id_list: List[int]) -> (pd.DataFrame, dict):
        """
        获取选取的测试数据 -> 用于统计分析
        如果 chart_df 是None 就用 df 中的数据
        :param test_id_list:
        :return:
            1. df
            2. calculation_capability
        """
        # if not test_id_list:
        #     raise Exception("get_unstack_data_to_csv_or_jmp_or_altair must have test_id")
        if self.to_chart_csv_data.chart_df is None:
            df = self.to_chart_csv_data.df
        else:
            df = self.to_chart_csv_data.chart_df
        name_dict = {}
        calculation_capability = {}
        for test_id in test_id_list:
            row = self.capability_key_dict[test_id]
            name_dict[test_id] = row["TEXT"]
            calculation_capability[row["TEXT"]] = row
        # rename -> key_id rename text
        df = df[GlobalVariable.JMP_SCRIPT_HEAD + test_id_list].copy()
        # {group}@{da_group}
        df["ALL_GROUP"] = df["GROUP"] + "@" + df["DA_GROUP"]
        if self.to_chart_csv_data.select_group is not None:
            df = df[df.ALL_GROUP.isin(self.to_chart_csv_data.select_group)]
        df = df.rename(columns=name_dict)
        return df, calculation_capability

    def calculation_group(self, group_params: Union[list, None], da_group_params: Union[list, None]):
        """
        分组的制程能力报表
        TODO: future
        :param group_params:
        :param da_group_params:
        :return:
        """

    def update_limit(self, limit_new: Dict[int, Tuple[float, float, str, str]], only_pass: bool = False) -> bool:
        """
        基于原始数据重新计算使用新limit的fail rate
        不修改原始数据，只是重新计算制程能力指标
        :param limit_new: {TEST_ID: (LO_LIMIT, HI_LIMIT, LO_TYPE, HI_TYPE)}
        :param only_pass: 是否只保留PASS数据
        :return: 更新是否成功
        """
        if self.df_module is None:
            self.QStatusMessage.emit("请先将数据载入到数据空间中!")
            return False

        try:
            # 保存原始数据（如果还没保存）
            if self._original_df_module is None:
                self._original_df_module = self._deep_copy_datamodule(self.df_module)

            # 保存当前limit变更
            self._current_limit_changes = limit_new.copy()

            # 基于原始数据和新limit重新计算制程能力
            self._calculate_with_new_limits(limit_new, only_pass)

            # 更新操作状态
            self._operation_state = 'limit_changed'

            # 发送更新信号
            self.update()
            self.QStatusMessage.emit("基于新Limit重新计算完成！可以查看新的fail rate结果。")
            return True

        except Exception as e:
            self.QStatusMessage.emit(f"Limit重新计算失败: {str(e)}")
            return False

    def _deep_copy_datamodule(self, df_module: DataModule) -> DataModule:
        """
        深拷贝DataModule对象
        """
        import copy
        return DataModule(
            prr_df=df_module.prr_df.copy(),
            dtp_df=df_module.dtp_df.copy(),
            ptmd_df=df_module.ptmd_df.copy()
        )

    def _calculate_with_new_limits(self, limit_new: Dict[int, Tuple[float, float, str, str]], only_pass: bool = False):
        """
        基于原始数据和新limit计算制程能力
        只对limit有变化的项目重新计算，其他项目保持原始结果
        同时在capability结果中添加NEW_LO_LIMIT和NEW_HI_LIMIT信息
        """
        # 获取原始的capability结果作为基础
        # 如果还没有原始结果，先计算一次
        if not hasattr(self, '_original_capability_key_list') or self._original_capability_key_list is None:
            self._original_capability_key_list = [item.copy() for item in self.capability_key_list]
            self._original_top_fail_dict = self.top_fail_dict.copy()

        # 检查哪些测试项目的limit真正发生了变化
        changed_test_ids = set()
        for test_id, (new_lo_limit, new_hi_limit, lo_type, hi_type) in limit_new.items():
            # 从原始ptmd中获取原始limit
            original_ptmd = self._original_df_module.ptmd_df[
                self._original_df_module.ptmd_df['TEST_ID'] == test_id
            ]
            if len(original_ptmd) > 0:
                original_lo_limit = original_ptmd.iloc[0]['LO_LIMIT']
                original_hi_limit = original_ptmd.iloc[0]['HI_LIMIT']

                # 只有当limit真正变化时才标记为需要重新计算
                limit_changed = (abs(new_lo_limit - original_lo_limit) > 1e-9 or
                                abs(new_hi_limit - original_hi_limit) > 1e-9)

                if limit_changed:
                    changed_test_ids.add(test_id)
                else:
                    # 特殊情况：即使limit值相同，但如果原始limit相等（LO_LIMIT == HI_LIMIT）
                    # 且不是全部fail，也不应该重新计算
                    # 这种情况下，保持原始结果
                    pass  # 不添加到changed_test_ids，保持原始结果

        # 如果没有任何limit变化，直接返回原始结果
        if len(changed_test_ids) == 0:
            # 为所有项目添加NEW_LO_LIMIT和NEW_HI_LIMIT字段（使用原始值）
            for item in self.capability_key_list:
                item['NEW_LO_LIMIT'] = item['LO_LIMIT']
                item['NEW_HI_LIMIT'] = item['HI_LIMIT']
                item['RESCUED_FAIL_COUNT'] = 0
                item['NEW_FAIL_RATE'] = item['FAIL_RATE']
            return

        # 只对limit有变化的项目重新计算
        # 创建临时的ptmd_df副本用于计算
        temp_ptmd_df = self._original_df_module.ptmd_df.copy()

        # 只更新有变化的limit值
        for test_id in changed_test_ids:
            lo_limit, hi_limit, lo_type, hi_type = limit_new[test_id]
            mask = temp_ptmd_df['TEST_ID'] == test_id
            if mask.any():
                temp_ptmd_df.loc[mask, 'LO_LIMIT'] = lo_limit
                temp_ptmd_df.loc[mask, 'HI_LIMIT'] = hi_limit

        # 创建临时DataModule用于计算
        temp_df_module = DataModule(
            prr_df=self._original_df_module.prr_df.copy(),
            dtp_df=self._original_df_module.dtp_df.copy(),
            ptmd_df=temp_ptmd_df
        )

        # 使用新limit重新计算top fail
        temp_top_fail_dict = CapabilityUtils.calculation_new_top_fail(temp_df_module)

        # 重新计算制程能力
        temp_capability_key_list = CapabilityUtils.calculation_capability(temp_df_module, temp_top_fail_dict)

        # 创建结果字典，方便查找
        temp_capability_dict = {item['TEST_ID']: item for item in temp_capability_key_list}
        original_capability_dict = {item['TEST_ID']: item for item in self._original_capability_key_list}

        # 合并结果：对于limit有变化的使用新计算结果，否则使用原始结果
        final_capability_key_list = []
        final_top_fail_dict = {}

        for original_item in self._original_capability_key_list:
            test_id = original_item['TEST_ID']

            if test_id in changed_test_ids:
                # limit有变化，使用新计算的结果，但保持原始的LO_LIMIT和HI_LIMIT
                new_item = original_item.copy()  # 从原始项开始，保持原始limit值
                new_lo_limit, new_hi_limit, _, _ = limit_new[test_id]

                # 使用新计算的FAIL_QTY和FAIL_RATE
                temp_result = temp_capability_dict[test_id]
                new_item['FAIL_QTY'] = temp_result['FAIL_QTY']
                new_item['FAIL_RATE'] = temp_result['FAIL_RATE']

                # 添加新limit信息
                new_item['NEW_LO_LIMIT'] = new_lo_limit
                new_item['NEW_HI_LIMIT'] = new_hi_limit

                # 计算救回的fail数量
                rescued_count = self._calculate_rescued_fail_count(test_id, new_lo_limit, new_hi_limit)
                new_item['RESCUED_FAIL_COUNT'] = rescued_count

                # 新的fail rate
                new_item['NEW_FAIL_RATE'] = temp_result['FAIL_RATE']

                final_capability_key_list.append(new_item)
                final_top_fail_dict[test_id] = temp_top_fail_dict[test_id]
            else:
                # limit没有变化，使用原始结果
                original_item_copy = original_item.copy()
                original_item_copy['NEW_LO_LIMIT'] = original_item_copy['LO_LIMIT']
                original_item_copy['NEW_HI_LIMIT'] = original_item_copy['HI_LIMIT']
                original_item_copy['RESCUED_FAIL_COUNT'] = 0
                original_item_copy['NEW_FAIL_RATE'] = original_item_copy['FAIL_RATE']

                final_capability_key_list.append(original_item_copy)
                final_top_fail_dict[test_id] = self._original_top_fail_dict[test_id]

        # 更新当前显示的数据
        self.top_fail_dict = final_top_fail_dict
        self.capability_key_list = final_capability_key_list

        # 更新capability字典
        if self.capability_key_dict is None:
            self.capability_key_dict = dict()
        else:
            self.capability_key_dict.clear()
        for each in self.capability_key_list:
            self.capability_key_dict[each["TEST_ID"]] = each

    def _calculate_rescued_fail_count(self, test_id: int, new_lo_limit: float, new_hi_limit: float) -> int:
        """
        计算使用新limit可以救回的fail数量
        :param test_id: 测试项目ID
        :param new_lo_limit: 新的下限
        :param new_hi_limit: 新的上限
        :return: 救回的fail数量
        """
        try:
            # 获取原始数据中该测试项目的数据
            original_dtp = self._original_df_module.dtp_df[
                self._original_df_module.dtp_df.index.get_level_values('TEST_ID') == test_id
            ]

            if len(original_dtp) == 0:
                return 0

            # 获取原始limit
            original_ptmd = self._original_df_module.ptmd_df[
                self._original_df_module.ptmd_df['TEST_ID'] == test_id
            ]

            if len(original_ptmd) == 0:
                return 0

            original_lo_limit = original_ptmd.iloc[0]['LO_LIMIT']
            original_hi_limit = original_ptmd.iloc[0]['HI_LIMIT']

            # 找出原始limit下的fail数据
            original_fail_mask = (
                (original_dtp['RESULT'] < original_lo_limit) |
                (original_dtp['RESULT'] > original_hi_limit)
            )
            original_fail_data = original_dtp[original_fail_mask]

            if len(original_fail_data) == 0:
                return 0

            # 在原始fail数据中，找出新limit下可以pass的数据
            rescued_mask = (
                (original_fail_data['RESULT'] >= new_lo_limit) &
                (original_fail_data['RESULT'] <= new_hi_limit)
            )
            rescued_count = rescued_mask.sum()

            return int(rescued_count)

        except Exception as e:
            self.QStatusMessage.emit(f"计算救回fail数量失败: {str(e)}")
            return 0

    def calculation_new_limit(self):
        """
        计算新Limit的制程能力
        使用更新后的limit重新计算top fail和capability
        :return:
        """
        if self.df_module is None:
            return

        try:
            # 使用新的limit重新计算top fail
            self.top_fail_dict = CapabilityUtils.calculation_new_top_fail(self.df_module)

            # 重新计算制程能力
            self.capability_key_list = CapabilityUtils.calculation_capability(self.df_module, self.top_fail_dict)

            # 更新capability字典
            if self.capability_key_dict is None:
                self.capability_key_dict = dict()
            else:
                self.capability_key_dict.clear()
            for each in self.capability_key_list:
                self.capability_key_dict[each["TEST_ID"]] = each

        except Exception as e:
            self.QStatusMessage.emit(f"制程能力计算失败: {str(e)}")

    def _filter_pass_data_only(self):
        """
        只保留PASS数据，过滤掉FAIL数据
        """
        if self.df_module is None:
            return

        # 获取PASS的DIE_ID
        pass_die_ids = self.df_module.prr_df[self.df_module.prr_df['FAIL_FLAG'] == FailFlag.PASS].index

        # 过滤dtp_df，只保留PASS的数据
        self.df_module.dtp_df = self.df_module.dtp_df[
            self.df_module.dtp_df.index.get_level_values('DIE_ID').isin(pass_die_ids)
        ]

    def screen_df(self, test_ids: List[int]):
        """
        只对选中的测试项目进行分析
        这是第三步操作，基于前面的操作结果进行进一步筛选
        :param test_ids: 要保留的测试项目ID列表
        """
        if self.df_module is None:
            self.QStatusMessage.emit("请先将数据载入到数据空间中!")
            return

        # 检查是否有前置操作
        if self._operation_state is None:
            self.QStatusMessage.emit("建议先执行'改变Limit后重算Rate'操作!")

        try:
            # 筛选ptmd_df，只保留选中的测试项目
            self.df_module.ptmd_df = self.df_module.ptmd_df[
                self.df_module.ptmd_df['TEST_ID'].isin(test_ids)
            ]

            # 筛选dtp_df，只保留选中的测试项目数据
            self.df_module.dtp_df = self.df_module.dtp_df[
                self.df_module.dtp_df.index.get_level_values('TEST_ID').isin(test_ids)
            ]

            # 如果有limit变更，也要筛选相关的limit变更
            if self._current_limit_changes:
                filtered_limit_changes = {
                    test_id: limit_info
                    for test_id, limit_info in self._current_limit_changes.items()
                    if test_id in test_ids
                }
                self._current_limit_changes = filtered_limit_changes

            # 重新计算制程能力
            self.calculation_top_fail()
            self.calculation_capability()
            self.background_generation_data_use_to_chart_and_to_save_csv()

            # 更新操作状态
            self._operation_state = 'data_screened'

            # 发送更新信号
            self.update()
            self.QStatusMessage.emit(f"已筛选出{len(test_ids)}个测试项目进行分析!")

        except Exception as e:
            self.QStatusMessage.emit(f"数据筛选失败: {str(e)}")

    def reset_to_original_data(self) -> bool:
        """
        重置到原始数据状态
        :return: 重置是否成功
        """
        if self._original_df_module is None:
            self.QStatusMessage.emit("没有保存的原始数据!")
            return False

        try:
            # 恢复原始数据
            self.df_module = self._deep_copy_datamodule(self._original_df_module)

            # 重新计算制程能力
            self.calculation_top_fail()
            self.calculation_capability()
            self.background_generation_data_use_to_chart_and_to_save_csv()

            # 清除操作状态
            self._operation_state = None
            self._current_limit_changes = None

            # 发送更新信号
            self.update()
            self.QStatusMessage.emit("已重置到原始数据状态!")
            return True

        except Exception as e:
            self.QStatusMessage.emit(f"重置失败: {str(e)}")
            return False

    def restore_original_limits(self) -> bool:
        """
        还原到原始limit，但保持当前的数据状态
        这是pushButton_2的新功能：针对新修改的limit进行还原
        :return: 还原是否成功
        """
        if self._operation_state != 'limit_changed':
            self.QStatusMessage.emit("请先执行'改变Limit后重算Rate'操作!")
            return False

        if self._original_df_module is None:
            self.QStatusMessage.emit("没有保存的原始数据!")
            return False

        try:
            # 重新计算制程能力（使用原始limit）
            self.calculation_top_fail()
            self.calculation_capability()
            self.background_generation_data_use_to_chart_and_to_save_csv()

            # 清除limit变更记录，但保持操作状态
            self._current_limit_changes = None
            self._operation_state = 'limit_restored'

            # 发送更新信号
            self.update()
            self.QStatusMessage.emit("已还原到原始limit，可以重新修改limit进行计算!")
            return True

        except Exception as e:
            self.QStatusMessage.emit(f"还原limit失败: {str(e)}")
            return False

    def drop_data_by_select_limit(self, func: str, limit_new: Dict[int, Tuple[float, float, str, str]]) -> bool:
        """
        基于第一步的limit变更结果，删除选中项目的limit内或limit外数据
        这是第二步操作，基于第一步的limit变更
        :param func: "inner"(删除limit内数据) 或 "outer"(删除limit外数据)
        :param limit_new: {TEST_ID: (LO_LIMIT, HI_LIMIT, LO_TYPE, HI_TYPE)}
        :return: 操作是否成功
        """
        if self.df_module is None:
            self.QStatusMessage.emit("请先将数据载入到数据空间中!")
            return False

        if self._operation_state != 'limit_changed':
            self.QStatusMessage.emit("请先执行'改变Limit后重算Rate'操作!")
            return False

        try:
            # 使用第一步保存的limit变更，如果没有传入新的limit
            if not limit_new and self._current_limit_changes:
                limit_new = self._current_limit_changes
            elif not limit_new:
                self.QStatusMessage.emit("没有找到limit变更信息!")
                return False

            die_ids_to_remove = set()

            for test_id, (lo_limit, hi_limit, lo_type, hi_type) in limit_new.items():
                # 从原始数据中获取该测试项目的数据
                test_data = self._original_df_module.dtp_df[
                    self._original_df_module.dtp_df.index.get_level_values('TEST_ID') == test_id
                ]

                if len(test_data) == 0:
                    continue

                # 根据新的limit判断哪些数据需要删除
                if func == "inner":
                    # 删除limit内的数据（保留limit外的数据）
                    mask = (test_data['RESULT'] >= lo_limit) & (test_data['RESULT'] <= hi_limit)
                elif func == "outer":
                    # 删除limit外的数据（保留limit内的数据）
                    mask = (test_data['RESULT'] < lo_limit) | (test_data['RESULT'] > hi_limit)
                else:
                    self.QStatusMessage.emit("参数错误: func必须为'inner'或'outer'")
                    return False

                # 收集需要删除的DIE_ID
                die_ids_to_remove.update(
                    test_data[mask].index.get_level_values('DIE_ID').tolist()
                )

            if die_ids_to_remove:
                # 从当前数据中删除相应的DIE（实际修改数据）
                self.df_module.prr_df = self.df_module.prr_df[
                    ~self.df_module.prr_df.index.isin(die_ids_to_remove)
                ]

                self.df_module.dtp_df = self.df_module.dtp_df[
                    ~self.df_module.dtp_df.index.get_level_values('DIE_ID').isin(die_ids_to_remove)
                ]

                # 重新计算制程能力（基于实际数据）
                self.calculation_top_fail()
                self.calculation_capability()
                self.background_generation_data_use_to_chart_and_to_save_csv()

                # 更新操作状态
                self._operation_state = 'data_filtered'

                # 发送更新信号
                self.update()

                action_desc = "limit内" if func == "inner" else "limit外"
                self.QStatusMessage.emit(f"已删除{len(die_ids_to_remove)}个DIE的{action_desc}数据!")
                return True
            else:
                self.QStatusMessage.emit("没有找到需要删除的数据!")
                return False

        except Exception as e:
            self.QStatusMessage.emit(f"数据删除失败: {str(e)}")
            return False

    def verify_pass_have_nan(self) -> bool:
        """ PASS的数据中含有空值! 不被允许, 检测的时候要定位到ID, 用来检测程序错误的 """

    def verify_test_no_repetition(self) -> bool:
        """ 除了MPR外有重复的TEST_NO! 检测的时候要定位到ID, 用来检测程序不标准的 """

    def show_limit_diff(self):
        """
        显示导入的STDF见Limit之间的差异
        :return:
        """
        if self.df_module is None:
            return self.QStatusMessage.emit("请先将数据载入到数据空间中!")
        # TODO:使用多进程后台处理(多进程可以实时修改代码,较为方便)
        p = Process(target=OpenXl.excel_limit_run, kwargs={
            'summary_df': self.select_summary,
            "limit_df": self.df_module.ptmd_df,
        })
        p.start()
        # OpenXl.excel_limit_run(self.select_summary, self.df_module.ptmd_df)

    def get_text_by_test_id(self, test_id: int):
        row = self.capability_key_dict[test_id]
        return row["TEXT"]

    def update(self):
        """
        主要是可以更新Table界面上的制程能力报告, 比如limit更新后重新计算
        :return:
        """
        print("update all QCalculation @emit")
        self.QCalculation.emit()

    def select_chart(self):
        """
        主要是用来选取绘图的数据, 在数据还是处于当前分组的一个状态下
        :return:
        """
        print("select_chart QChartSelect @emit")
        self.QChartSelect.emit()

    def refresh_chart(self):
        """
        这个主要是数据有突然的变化, 比如分组改变了, 触发这个后把绘图的数据刷新重新绘图, 不Select
        :return:
        """
        print("refresh_chart QChartRefresh @emit")
        self.QChartRefresh.emit()
