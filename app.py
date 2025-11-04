#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

"""
@File    : app.py
@Author  : Link
@Time    : 2022/12/16 21:24
@Mark    :
@Version : V3.0
@START_T : 20220814
@RELEASE :
"""

import sys
import logging
from datetime import datetime

from PySide2.QtCore import Signal, QObject
from PySide2.QtGui import QCloseEvent
from PySide2.QtWidgets import QApplication

from ui_component.ui_common.my_text_browser import UiMessage
from ui_component.ui_main.ui_main import Application, Main_Ui
from common.logger_config import LoggerManager

import warnings

warnings.filterwarnings("ignore")


class Stream(QObject):
    conn = True
    newText = Signal(str)
    logger = None

    def write(self, text):
        if not self.conn:
            return
        self.newText.emit(str(text))
        # 使用logger记录
        if self.logger and text.strip():
            self.logger.info(text.rstrip())
        # 实时刷新界面
        QApplication.processEvents()


class main_ui(Main_Ui):

    def __init__(self, parent=None, license_control=False):
        super(main_ui, self).__init__(parent=parent, license_control=license_control)
        self.setWindowTitle("STDF Data Analysis System")
        
        # 初始化日志管理器
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.setup_logger(
            log_file='logger.log',
            max_bytes=10*1024,  # 10KB用于测试
            backup_count=5  # 保留5个备份
        )
        self.logger_manager.log_app_start()
        
        # 将logger传递给 TextBrowser
        if hasattr(self, 'text_browser'):
            self.text_browser.logger = self.logger
        
        self.sd = Stream()
        self.se = Stream()
        self.sd.logger = self.logger
        self.se.logger = self.logger
        self.sd.newText.connect(self.outputWritten)
        self.se.newText.connect(self.errorWritten)
        sys.stdout = self.sd
        sys.stderr = self.se

    def outputWritten(self, text: str):
        """
        根据规则来打印合适颜色的信息
        :param text:
        :return:
        """
        self.text_browser.split_append(text)

    def errorWritten(self, text: str):
        self.text_browser.m_append(
            UiMessage.error(text)
        )

    def closeEvent(self, a0: QCloseEvent) -> None:
        sys.stdout.conn = False
        sys.stderr.conn = False
        # 记录应用关闭
        if hasattr(self, 'logger_manager'):
            self.logger_manager.log_app_close()
        sys.exit(0)


if __name__ == '__main__':
    """
    开源版
    """
    import multiprocessing
    from ui_component.ui_app_variable import UiGlobalVariable
    from common.app_variable import GlobalVariable

    GlobalVariable.init()
    # 打包后使用PyQtGraph内置颜色，避免路径问题
    # 开发环境可以设置为True使用本地颜色文件
    UiGlobalVariable.GraphUseLocalColor = False
    multiprocessing.freeze_support()
    app = Application(sys.argv)
    app.setApplicationName("IC DATA ANALYSIS")
    try:
        win = main_ui(license_control=False)
        app.setWindowIcon(win.icon)
        win.show()
        sys.exit(app.exec_())
    except Exception as err:
        # 打包后避免设置sys.stdout = None，会导致多进程错误
        import traceback
        traceback.print_exc()
    finally:
        pass  # 打包后避免print，可能导致多进程错误
