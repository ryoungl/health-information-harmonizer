import subprocess
import sys
from pathlib import Path

# 获取当前 Python 解释器的路径
PYTHON_EXE = sys.executable 

def run_update():
    print(f"开始从 FDA 采集数据 (使用: {PYTHON_EXE})...")
    result_a = subprocess.run([PYTHON_EXE, "scripts/build_openfda_db_from_seed_list.py", "--verbose"])
    
    if result_a.returncode != 0:
        print("采集脚本出错，请检查网络或 common_generics_en.txt 内容。")
        return

    print("\n正在将原始数据转换为系统格式...")
    result_b = subprocess.run([PYTHON_EXE, "scripts/convert_openfda_raw_to_structured.py", "--verbose"])
    
    if result_b.returncode == 0:
        print("\n[成功] 数据库已更新！现在可以启动 main.py 了。")
    else:
        print("\n[失败] 转换过程中出现问题。")

if __name__ == "__main__":
    run_update()