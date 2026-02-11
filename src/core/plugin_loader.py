"""
插件加载器和安全验证
"""
import ast
import importlib
import sys
from typing import Dict, Any, Optional, Type, List, Tuple
from pathlib import Path
import hashlib

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.collectors.base import BaseCollector
from src.core.models import CollectionResult


class PluginSecurityError(Exception):
    """插件安全错误"""
    pass


class PluginLoader:
    """插件加载器（带安全验证）"""
    
    # 禁止的模块和函数
    FORBIDDEN_MODULES = {
        # 系统操作（危险）
        'subprocess', 'socket', 'sys', 'importlib',
        # 代码执行（危险）
        'eval', 'exec', 'compile', '__import__',
        # 文件操作（危险，但允许通过pathlib等安全方式）
        'file', 'input', 'raw_input'
        # 注意：'os' 已从禁止列表中移除，因为文件系统采集器需要 os.access 等安全操作
    }
    
    # 允许的导入模块（白名单）
    ALLOWED_IMPORTS = {
        # 标准库 - 基础类型和工具
        'typing', 'datetime', 'json', 'hashlib', 'uuid',
        'pathlib', 're', 'collections', 'itertools',
        'math', 'random', 'string', 'ast',
        # 标准库 - 网络和URL处理
        'urllib',
        # 标准库 - 文件系统（受限使用，仅用于文件权限检查）
        'os',
        # 第三方库 - 数据库
        'sqlalchemy',
        # 第三方库 - 图数据库
        'neo4j', 'falkordb',
        # 第三方库 - Git操作
        'git'
    }
    
    # 允许的BaseCollector相关导入
    COLLECTOR_IMPORTS = {
        'zen.metadata.core.models',
        'zen.metadata.core.collectors.base',
        'src.core.models',
        'src.core.collectors.base',
        '..core.models',
        '..core.collectors.base'
    }
    
    def __init__(self, plugins_dir: str = "plugins"):
        """
        初始化插件加载器
        
        Args:
            plugins_dir: 插件目录
        """
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_plugins: Dict[str, Type[BaseCollector]] = {}
        self.plugin_checksums: Dict[str, str] = {}
    
    def validate_code(self, code: str, filename: str = "plugin.py") -> Tuple[bool, Optional[str]]:
        """
        验证插件代码安全性
        
        Args:
            code: 代码内容
            filename: 文件名（用于错误提示）
            
        Returns:
            (是否安全, 错误信息)
        """
        try:
            # 解析AST
            tree = ast.parse(code, filename=filename)
            
            # 检查禁止的导入和函数调用
            for node in ast.walk(tree):
                # 检查导入
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        if module_name in self.FORBIDDEN_MODULES:
                            return False, f"禁止导入模块: {module_name}"
                        if module_name not in self.ALLOWED_IMPORTS and not any(
                            module_name.startswith(prefix) for prefix in ['zen.', 'src.', '..']
                        ):
                            # 允许相对导入和项目内部导入
                            if not any(module_name.startswith(prefix) for prefix in ['zen.', 'src.', '..']):
                                return False, f"不允许导入模块: {module_name}（不在白名单中）"
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        if module_name in self.FORBIDDEN_MODULES:
                            return False, f"禁止从模块导入: {module_name}"
                
                # 检查函数调用
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.FORBIDDEN_MODULES:
                            return False, f"禁止调用函数: {node.func.id}"
                    elif isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            if node.func.value.id in self.FORBIDDEN_MODULES:
                                return False, f"禁止调用模块函数: {node.func.value.id}.{node.func.attr}"
            
            # 检查是否继承自BaseCollector
            has_collector = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            if base.id == 'BaseCollector':
                                has_collector = True
                                break
                        elif isinstance(base, ast.Attribute):
                            if base.attr == 'BaseCollector':
                                has_collector = True
                                break
            
            if not has_collector:
                return False, "插件类必须继承自 BaseCollector"
            
            return True, None
            
        except SyntaxError as e:
            return False, f"代码语法错误: {str(e)}"
        except Exception as e:
            return False, f"代码验证失败: {str(e)}"
    
    def load_plugin_from_code(self, code: str, plugin_name: str) -> Type[BaseCollector]:
        """
        从代码字符串加载插件
        
        Args:
            code: 插件代码
            plugin_name: 插件名称
            
        Returns:
            采集器类
        """
        # 验证代码安全性
        is_safe, error = self.validate_code(code, f"{plugin_name}.py")
        if not is_safe:
            raise PluginSecurityError(f"插件代码不安全: {error}")
        
        # 计算代码校验和
        checksum = hashlib.sha256(code.encode()).hexdigest()
        
        # 如果插件已加载且代码未变化，直接返回
        if plugin_name in self.loaded_plugins:
            if self.plugin_checksums.get(plugin_name) == checksum:
                return self.loaded_plugins[plugin_name]
        
        # 创建临时模块
        module_name = f"plugin_{plugin_name}_{checksum[:8]}"
        
        # 编译并执行代码
        try:
            compiled_code = compile(code, f"<plugin:{plugin_name}>", "exec")
            module = type(sys.modules[__name__])(module_name)
            sys.modules[module_name] = module
            
            # 注入必要的导入
            exec_globals = {
                '__name__': module_name,
                '__file__': f"<plugin:{plugin_name}>",
                'BaseCollector': BaseCollector,
                'CollectionResult': CollectionResult,
                'MetadataEntity': None,  # 将在执行时从导入获取
                'MetadataRelationship': None,
                'MetadataType': None,
                'RelationshipType': None,
            }
            
            # 执行代码
            exec(compiled_code, exec_globals)
            
            # 查找采集器类
            collector_class = None
            for name, obj in exec_globals.items():
                if (isinstance(obj, type) and 
                    issubclass(obj, BaseCollector) and 
                    obj != BaseCollector):
                    collector_class = obj
                    break
            
            if collector_class is None:
                raise ValueError(f"在插件 {plugin_name} 中未找到继承自 BaseCollector 的类")
            
            # 缓存插件
            self.loaded_plugins[plugin_name] = collector_class
            self.plugin_checksums[plugin_name] = checksum
            
            return collector_class
            
        except Exception as e:
            raise PluginSecurityError(f"加载插件失败: {str(e)}")
    
    def load_plugin_from_file(self, file_path: Path) -> Type[BaseCollector]:
        """
        从文件加载插件
        
        Args:
            file_path: 插件文件路径
            
        Returns:
            采集器类
        """
        plugin_name = file_path.stem
        
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        return self.load_plugin_from_code(code, plugin_name)
    
    def save_plugin(self, code: str, filename: str) -> Path:
        """
        保存插件到文件
        
        Args:
            code: 插件代码
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        # 验证代码
        is_safe, error = self.validate_code(code, filename)
        if not is_safe:
            raise PluginSecurityError(f"插件代码不安全: {error}")
        
        # 保存文件
        file_path = self.plugins_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return file_path
    
    def reload_plugin(self, plugin_name: str) -> Type[BaseCollector]:
        """
        重新加载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            采集器类
        """
        # 从缓存中移除
        if plugin_name in self.loaded_plugins:
            del self.loaded_plugins[plugin_name]
        
        # 从文件重新加载
        file_path = self.plugins_dir / f"{plugin_name}.py"
        if file_path.exists():
            return self.load_plugin_from_file(file_path)
        else:
            raise FileNotFoundError(f"插件文件不存在: {file_path}")
    
    def get_plugin(self, plugin_name: str) -> Optional[Type[BaseCollector]]:
        """
        获取已加载的插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            采集器类，如果未加载则返回None
        """
        return self.loaded_plugins.get(plugin_name)
    
    def list_plugins(self) -> List[str]:
        """
        列出所有已加载的插件
        
        Returns:
            插件名称列表
        """
        return list(self.loaded_plugins.keys())

