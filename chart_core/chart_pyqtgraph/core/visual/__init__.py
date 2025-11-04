# Visual module init file
try:
    from .visual import *
except ImportError:
    # 如果无法导入编译的模块，提供一个空的实现或跳过
    pass
