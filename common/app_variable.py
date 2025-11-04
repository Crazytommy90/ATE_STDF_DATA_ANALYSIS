"""
-*- coding: utf-8 -*-
@Author  : Link
@Time    : 2021/12/16 9:21
@Software: PyCharm
@File    : app_variable.py
@Remark  : 
"""
import os
from dataclasses import dataclass
from typing import Union, Dict

import pandas as pd
from numpy import (
    uint8 as U1,
    uint16 as U2,
    uint32 as U4,
    int8 as I1,
    int16 as I2,
    int32 as I4,
    float32 as R4,
    float64 as R8,
    nan
)


# 尽可能将数据类型都定义为 dataclass 或是 nametuple, 比dict数据容易操作, 最好是nametuple

@dataclass
class PtmdModule:
    ID: int  # UI赋予的ID
    TEST_ID: int
    DATAT_TYPE: str
    TEST_NUM: int
    TEST_TXT: str
    PARM_FLG: int
    OPT_FLAG: int
    RES_SCAL: int
    LLM_SCAL: int
    HLM_SCAL: int
    LO_LIMIT: float
    HI_LIMIT: float
    UNITS: str
    TEXT: str


@dataclass
class Calculation:
    """
    暂未用到
    """
    TEST_ID: int
    TEST_TYPE: str
    TEST_NUM: int
    TEST_TXT: str
    UNITS: str
    LO_LIMIT: float
    HI_LIMIT: float
    AVG: float
    STD: float
    CPK: float
    QTY: int
    FAIL_QTY: int
    FAIL_RATE: float
    REJECT_QTY: int
    REJECT_RATE: float
    MIN: float
    MAX: float
    LO_LIMIT_TYPE: Union[str, float]
    HI_LIMIT_TYPE: Union[str, float]
    ALL_DATA_MIN: float
    ALL_DATA_MAX: float
    TEXT: str


@dataclass
class DataLiBackup:
    select_summary: pd.DataFrame = None
    prr_df: pd.DataFrame = None


@dataclass
class ToChartCsv:
    # TODO: Must
    df: pd.DataFrame = None
    group_df: Dict[str, pd.DataFrame] = None
    chart_df: pd.DataFrame = None
    group_chart_df: Dict[str, pd.DataFrame] = None
    select_group: set = None

    # TODO: Optional PAT
    limit: pd.DataFrame = None
    group_limit: Dict[str, pd.DataFrame] = None


@dataclass
class DataModule:
    """
    数据空间整合后的数据模型
    """
    prr_df: pd.DataFrame = None
    dtp_df: pd.DataFrame = None  # 数据
    ptmd_df: pd.DataFrame = None  # 测试项目相关


class DatatType:
    FTR: str = "FTR"
    PTR: str = "PTR"
    MPR: str = "MPR"


class FailFlag:
    PASS = 1
    FAIL = 0


class LimitType:
    NoHighLimit = "NA"
    EqualHighLimit = "LE"
    ThenHighLimit = "LT"

    NoLowLimit = "NA"
    EqualLowLimit = "GE"
    ThenLowLimit = "GT"


class PartFlags:
    ALL = 0
    FIRST = 1
    RETEST = 2
    FINALLY = 3
    XY_COORD = 4
    PART_FLAGS = ('ALL', 'FIRST', 'RETEST', 'FINALLY', "XY_COORD")


class GlobalVariable:
    """
    用来放一些全局变量
    TODO: 以大写作为主要的HEAD
    """
    DEBUG = True
    SAVE_PKL = False  # 用来将数据保存到二进制数据中用来做APP测试 TODO: 此版本暂时作废

    # 动态确定缓存路径，优先使用C盘，如果不可用则使用系统临时目录
    @staticmethod
    def _get_cache_base_path():
        """
        获取缓存基础路径，优先使用C盘，如果不可用则使用系统临时目录
        """
        import tempfile

        # 优先尝试C盘
        c_drive_path = r"C:\1_STDF"
        try:
            if not os.path.exists(c_drive_path):
                os.makedirs(c_drive_path, exist_ok=True)
            # 测试是否可写
            test_file = os.path.join(c_drive_path, "test_write.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return c_drive_path
        except (OSError, PermissionError):
            # C盘不可用，使用系统临时目录
            temp_base = os.path.join(tempfile.gettempdir(), "STDF_CACHE_FALLBACK")
            os.makedirs(temp_base, exist_ok=True)
            return temp_base


# 在类外部调用静态方法来初始化路径
def _get_cache_base_path():
    """
    获取缓存基础路径，优先使用C盘，如果不可用则使用系统临时目录
    """
    import tempfile

    # 优先尝试C盘
    c_drive_path = r"C:\1_STDF"
    try:
        if not os.path.exists(c_drive_path):
            os.makedirs(c_drive_path, exist_ok=True)
        # 测试是否可写
        test_file = os.path.join(c_drive_path, "test_write.tmp")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        return c_drive_path
    except (OSError, PermissionError):
        # C盘不可用，使用系统临时目录
        temp_base = os.path.join(tempfile.gettempdir(), "STDF_CACHE_FALLBACK")
        os.makedirs(temp_base, exist_ok=True)
        return temp_base


# 初始化缓存基础路径
GlobalVariable._CACHE_BASE = _get_cache_base_path()

# 设置所有路径
GlobalVariable.SQLITE_PATH = os.path.join(GlobalVariable._CACHE_BASE, "stdf_info.db")  # 用于存summary
GlobalVariable.CACHE_PATH = os.path.join(GlobalVariable._CACHE_BASE, "STDF_CACHE")
GlobalVariable.JMP_CACHE_PATH = os.path.join(GlobalVariable._CACHE_BASE, "JMP_CACHE")
GlobalVariable.LIMIT_PATH = os.path.join(GlobalVariable._CACHE_BASE, "LIMIT_CACHE")
GlobalVariable.NGINX_PATH = os.path.join(GlobalVariable._CACHE_BASE, "NGINX_CACHE")

# 设置其他类属性
GlobalVariable.STD_SUFFIXES = {
    ".std",
    ".stdf",
    ".std_temp"  # py_ate
}
GlobalVariable.LOT_TREE_HEAD = (
    "ID", "LOT_ID", "SBLOT_ID", "WAFER_ID", "BLUE_FILM_ID", "TEST_COD", "FLOW_ID", "QTY", "PASS",
    "YIELD", "PART_TYP", "JOB_NAM", "NODE_NAM", "SITE_CNT", "START_T"
)
GlobalVariable.LOT_TREE_HEAD_LENGTH = len(GlobalVariable.LOT_TREE_HEAD)

GlobalVariable.PART_FLAGS = PartFlags.PART_FLAGS
GlobalVariable.FILE_TABLE_HEAD = ("READ_FAIL", "PART_FLAG", "MESSAGE", "LOT_ID", "SBLOT_ID", "WAFER_ID", "TEST_COD", "FLOW_ID",
                   "PART_TYP", "JOB_NAM", "NODE_NAM", "SETUP_T", "START_T", "TST_TEMP", "FILE_PATH")
GlobalVariable.SKIP_FILE_TABLE_DATA_HEAD = {"READ_FAIL", "PART_FLAG"}

# Save memory
GlobalVariable.PRR_HEAD = ("PART_ID", "HEAD_NUM", "SITE_NUM", "X_COORD", "Y_COORD", "HARD_BIN", "SOFT_BIN", "PART_FLG",
            "NUM_TEST", "FAIL_FLAG", "TEST_T")
GlobalVariable.PRR_TYPE = (U2, U1, U1, I2, I2, U2, U2, U1, U2, U1, U4,)
GlobalVariable.PRR_TYPE_DICT = dict(zip(GlobalVariable.PRR_HEAD, GlobalVariable.PRR_TYPE))

GlobalVariable.DTP_HEAD = ("PART_ID", "TEST_ID", "RESULT", "TEST_FLG", "PARM_FLG", "OPT_FLAG", "LO_LIMIT", "HI_LIMIT")
GlobalVariable.DTP_TYPE = (U2, U4, R4, U1, U1, U1, R4, R4)
GlobalVariable.DTP_TYPE_DICT = dict(zip(GlobalVariable.DTP_HEAD, GlobalVariable.DTP_TYPE))

GlobalVariable.PTMD_HEAD = ("TEST_ID", "DATAT_TYPE", "TEST_NUM", "TEST_TXT", "PARM_FLG", "OPT_FLAG", "RES_SCAL", "LLM_SCAL",
             "HLM_SCAL", "LO_LIMIT", "HI_LIMIT", "UNITS")
GlobalVariable.PTMD_TYPE = (U2, str, U4, str, U1, U1, I1, I1, I1, R4, R4, str)
GlobalVariable.PTMD_TYPE_DICT = dict(zip(GlobalVariable.PTMD_HEAD, GlobalVariable.PTMD_TYPE))

GlobalVariable.JMP_SCRIPT_HEAD = ["GROUP", "DA_GROUP", "PART_ID", "X_COORD", "Y_COORD", "HARD_BIN", "SOFT_BIN"]

# 列名常量（用于动态查找列索引）
GlobalVariable.TEST_ID_COLUMN_NAME = "TEST_ID"
GlobalVariable.TEST_TYPE_COLUMN_NAME = "TEST_TYPE"
GlobalVariable.TEST_NUM_COLUMN_NAME = "TEST_NUM"
GlobalVariable.TEST_TXT_COLUMN_NAME = "TEST_TXT"
GlobalVariable.CPK_COLUMN_NAME = "CPK"
GlobalVariable.TOP_FAIL_COLUMN_NAME = "FAIL_QTY"  # Top Fail使用FAIL_QTY列
GlobalVariable.REJECT_COLUMN_NAME = "REJECT_QTY"

# 保留原有列索引常量（向后兼容，但不再推荐使用）
GlobalVariable.TEST_ID_COLUMN = 0
GlobalVariable.TEST_TYPE_COLUMN = 1
GlobalVariable.TEST_NUM_COLUMN = 2
GlobalVariable.TEST_TXT_COLUMN = 3
GlobalVariable.LO_LIMIT_COLUMN = 5
GlobalVariable.HI_LIMIT_COLUMN = 6
GlobalVariable.NEW_LO_LIMIT_COLUMN = 7
GlobalVariable.NEW_HI_LIMIT_COLUMN = 8
GlobalVariable.CPK_COLUMN = 9
GlobalVariable.TOP_FAIL_COLUMN = 11
GlobalVariable.REJECT_COLUMN = 13
GlobalVariable.NEW_FAIL_RATE_COLUMN = 14
GlobalVariable.RESCUED_FAIL_COUNT_COLUMN = 15
GlobalVariable.LO_LIMIT_TYPE_COLUMN = 17
GlobalVariable.HI_LIMIT_TYPE_COLUMN = 18

GlobalVariable.CPK_LO = 0
GlobalVariable.CPK_HI = 1
GlobalVariable.TOP_FAIL_LO = 0
GlobalVariable.REJECT_LO = 0

# 添加init静态方法到GlobalVariable类
def _init_global_variable():
    if not os.path.exists(GlobalVariable.CACHE_PATH):
        os.makedirs(GlobalVariable.CACHE_PATH)
    if not os.path.exists(GlobalVariable.JMP_CACHE_PATH):
        os.makedirs(GlobalVariable.JMP_CACHE_PATH)

GlobalVariable.init = staticmethod(_init_global_variable)


class TestVariable:
    """
    用于测试的各种路径
    """
    TEMP_PATH = os.getenv("TEMP")

    TEMP_PRR_PATH = os.path.join(TEMP_PATH, "StdfTempPrr.csv")
    TEMP_DTP_PATH = os.path.join(TEMP_PATH, "StdfTempDtp.csv")
    TEMP_PTMD_PATH = os.path.join(TEMP_PATH, "StdfTempPtmd.csv")
    TEMP_BIN_PATH = os.path.join(TEMP_PATH, "StdfTempHardSoftBin.csv")

    PATHS = (TEMP_PRR_PATH, TEMP_DTP_PATH, TEMP_PTMD_PATH, TEMP_BIN_PATH)

    # 使用动态路径替代硬编码的D盘路径
    HDF5_PATH = os.path.join(GlobalVariable.CACHE_PATH, "TEST_DATA.h5")
    HDF5_2_PATH = os.path.join(GlobalVariable.CACHE_PATH, "TEST.h5")
    HDF5_3_PATH = os.path.join(GlobalVariable.CACHE_PATH, "N49HT00000", "DEMO1_CP1.h5")
    # HDF5_PATH = r".\test_data\TEST.h5"

    TABLE_PICKLE_PATH = os.path.join(GlobalVariable.CACHE_PATH, '{}.pkl'.format("TABLE_DATA"))

    # 测试用路径，保持在临时目录或用户指定位置
    STDF_PATH = os.path.join(GlobalVariable._CACHE_BASE, "TEST_DATA.std")
    STDF_FILES_PATH = os.path.join(GlobalVariable._CACHE_BASE, "TEST_FILES")
