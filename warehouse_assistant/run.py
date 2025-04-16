"""
智能仓储助手的启动脚本
用于设置正确的Python模块导入路径并启动应用
"""
import sys
import os
from pathlib import Path

# 获取当前脚本所在目录
current_dir = Path(__file__).parent
# 获取项目根目录（包含warehouse_assistant的目录）
project_root = current_dir.parent

# 将项目根目录添加到Python模块搜索路径
sys.path.insert(0, str(project_root))

# 打印路径信息，便于调试
print(f"当前目录: {current_dir}")
print(f"项目根目录: {project_root}")
print(f"Python路径: {sys.path[0]}")

# 导入并运行服务
if __name__ == "__main__":
    import uvicorn
    
    # 进入项目根目录，确保相对路径正确
    os.chdir(str(project_root))
    
    # 启动FastAPI应用
    uvicorn.run(
        "warehouse_assistant.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式下启用热重载
        workers=1     # 使用单个工作进程，便于调试
    ) 