# PyInstaller hook for tables (PyTables)
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# 收集所有tables子模块
hiddenimports = collect_submodules('tables')

# 收集tables的数据文件
datas = collect_data_files('tables', include_py_files=True)

# 收集tables的动态库
binaries = collect_dynamic_libs('tables')

# 添加关键的隐藏导入
hiddenimports += [
    'tables.hdf5extension',
    'tables.utilsextension', 
    'tables.lrucacheextension',
    'tables._comp_lzo',
    'tables._comp_bzip2',
]