#!/usr/bin/env python3
"""
AI助教评估系统启动脚本

使用方法:
    python run.py                    # 默认配置启动
    python run.py --env dev          # 开发环境
    python run.py --env prod         # 生产环境
    python run.py --host 0.0.0.0 --port 8080  # 自定义主机和端口
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI助教评估系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py                     # 使用默认配置启动
  python run.py --env dev           # 开发环境启动  
  python run.py --env prod          # 生产环境启动
  python run.py --host 0.0.0.0 --port 8080  # 自定义主机端口
  python run.py --reload            # 启用热重载
  python run.py --workers 4         # 指定工作进程数
        """
    )
    
    parser.add_argument(
        "--env", "-e",
        choices=["dev", "prod", "test"],
        default="dev",
        help="运行环境 (default: dev)"
    )
    
    parser.add_argument(
        "--host",
        default=None,
        help="服务器主机地址 (default: 从配置文件读取)"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="服务器端口 (default: 从配置文件读取)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用代码热重载 (仅开发环境)"
    )
    
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=1,
        help="工作进程数 (default: 1)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default=None,
        help="日志级别 (default: 从配置文件读取)"
    )
    
    parser.add_argument(
        "--access-log",
        action="store_true",
        default=True,
        help="启用访问日志"
    )
    
    args = parser.parse_args()
    
    # 设置环境变量
    if args.env == "dev":
        os.environ["ENVIRONMENT"] = "development"
        os.environ["DEBUG"] = "true"
    elif args.env == "prod":
        os.environ["ENVIRONMENT"] = "production"  
        os.environ["DEBUG"] = "false"
    elif args.env == "test":
        os.environ["ENVIRONMENT"] = "testing"
        os.environ["DEBUG"] = "true"
    
    # 导入配置和应用
    try:
        from src.config import get_settings
        settings = get_settings()
        
        # 命令行参数覆盖配置文件设置
        host = args.host or settings.host
        port = args.port or settings.port
        log_level = args.log_level or settings.log_level.lower()
        
        # 启动信息
        print("🚀 正在启动 AI助教评估系统...")
        print(f"📝 环境: {settings.environment}")
        print(f"🌐 地址: http://{host}:{port}")
        print(f"📚 API文档: http://{host}:{port}/docs")
        print(f"💾 数据库: {settings.database_url}")
        print(f"📊 日志级别: {log_level}")
        
        if args.reload:
            print("🔄 热重载: 已启用")
        if args.workers > 1:
            print(f"👷 工作进程: {args.workers}")
            
        print("-" * 50)
        
        # 启动服务器
        import uvicorn
        
        uvicorn.run(
            "src.main:app",
            host=host,
            port=port,
            reload=args.reload and args.env == "dev",
            workers=args.workers if not args.reload else 1,
            log_level=log_level,
            access_log=args.access_log,
            # 生产环境配置
            loop="uvloop" if args.env == "prod" else "auto",
            http="httptools" if args.env == "prod" else "auto",
        )
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

