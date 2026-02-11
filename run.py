"""
Zen Metadata 快速启动脚本
"""
import uvicorn
import yaml
from pathlib import Path


def load_config():
    """加载配置"""
    config_path = Path("config/config.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def main():
    """主函数"""
    config = load_config()
    api_config = config.get('api', {})
    
    print("=" * 50)
    print("Zen Metadata - 统一元数据管理系统")
    print("=" * 50)
    print(f"API 服务启动中...")
    print(f"地址: http://{api_config.get('host', '0.0.0.0')}:{api_config.get('port', 8000)}")
    print(f"文档: http://{api_config.get('host', '0.0.0.0')}:{api_config.get('port', 8000)}/docs")
    print("=" * 50)
    
    uvicorn.run(
        "src.api.server:app",
        host=api_config.get('host', '0.0.0.0'),
        port=api_config.get('port', 8000),
        reload=api_config.get('debug', False),
        log_level="info"
    )


if __name__ == "__main__":
    main()





