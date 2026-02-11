"""
测试后端服务是否运行
"""
import requests
import sys

def test_backend():
    """测试后端服务"""
    try:
        # 测试健康检查端点
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("[OK] 后端服务运行正常")
            print(f"  服务状态: {data.get('status')}")
            print(f"  图数据库: {'[OK]' if data.get('services', {}).get('graph_store') else '[未连接]'}")
            print(f"  SQLite: {'[OK]' if data.get('services', {}).get('sqlite_processor') else '[未初始化]'}")
            print(f"  用户存储: {'[OK]' if data.get('services', {}).get('user_storage') else '[未初始化]'}")
            print(f"  认证服务: {'[OK]' if data.get('services', {}).get('auth_service') else '[未初始化]'}")
            return True
        else:
            print(f"[ERROR] 后端服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] 无法连接到后端服务 (http://localhost:8000)")
        print("  请确保后端服务已启动:")
        print("    python run.py")
        print("  或")
        print("    uvicorn src.api.server:app --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_backend()
    sys.exit(0 if success else 1)

