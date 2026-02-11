"""测试后端服务是否运行。"""

import json
import sys
import urllib.error
import urllib.request

import pytest


HEALTH_URL = "http://localhost:8000/health"


def check_backend_health(verbose: bool = True) -> bool:
    """检查后端服务健康状态并输出可读信息。"""
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as response:
            status_code = response.status
            payload = response.read().decode("utf-8")

        if status_code == 200:
            if verbose:
                data = json.loads(payload)
                print("[OK] 后端服务运行正常")
                print(f"  服务状态: {data.get('status')}")
                print(f"  图数据库: {'[OK]' if data.get('services', {}).get('graph_store') else '[未连接]'}")
                print(f"  SQLite: {'[OK]' if data.get('services', {}).get('sqlite_processor') else '[未初始化]'}")
                print(f"  用户存储: {'[OK]' if data.get('services', {}).get('user_storage') else '[未初始化]'}")
                print(f"  认证服务: {'[OK]' if data.get('services', {}).get('auth_service') else '[未初始化]'}")
            return True

        if verbose:
            print(f"[ERROR] 后端服务响应异常: {status_code}")
        return False
    except urllib.error.URLError:
        if verbose:
            print(f"[ERROR] 无法连接到后端服务 ({HEALTH_URL})")
            print("  请确保后端服务已启动:")
            print("    python run.py")
            print("  或")
            print("    uvicorn src.api.server:app --host 0.0.0.0 --port 8000")
        return False
    except Exception as exc:
        if verbose:
            print(f"[ERROR] 测试失败: {exc}")
        return False


def test_backend() -> None:
    """pytest 测试入口。"""
    if not check_backend_health(verbose=False):
        pytest.skip("backend service not running at http://localhost:8000")


if __name__ == "__main__":
    ok = check_backend_health(verbose=True)
    sys.exit(0 if ok else 1)
