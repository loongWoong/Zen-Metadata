"""
代码元数据采集器插件
支持 Python, JavaScript, Java, TypeScript 等
"""
from src.collectors.base import BaseCollector
from src.core.models import CollectionResult
from typing import Dict, Any, List, Optional
from pathlib import Path
import ast
import re

class CodeMetadataCollector(BaseCollector):
    """代码元数据采集器"""
    
    SUPPORTED_LANGUAGES = {
        'python': 'tree_sitter_python',
        'javascript': 'tree_sitter_javascript',
        'typescript': 'tree_sitter_typescript',
        'java': 'tree_sitter_java'
    }
    
    def collect(self) -> CollectionResult:
        """采集代码元数据"""
        result = CollectionResult()
        
        try:
            source_path = self.get_config("source_path")
            if not source_path:
                result.errors.append("缺少必需的配置: source_path")
                return result
            
            self.source_path = Path(source_path)
            self.languages = self.get_config("languages", ["python"])
            self.exclude_patterns = self.get_config("exclude_patterns", [])
            
            # 获取实体类型（从元模型配置中）
            entity_type = self.get_entity_type() or "CodeProject"
            
            # 创建项目实体
            project_entity = self.create_entity(
                entity_type=entity_type,
                name=self.source_path.name,
                description=f"代码项目: {self.source_path}",
                properties={
                    "path": str(self.source_path),
                    "languages": self.languages
                }
            )
            result.entities.append(project_entity)
            
            # 遍历文件
            for file_path in self._get_source_files():
                file_result = self._collect_file(file_path, project_entity.id)
                result.entities.extend(file_result.entities)
                result.relationships.extend(file_result.relationships)
                result.errors.extend(file_result.errors)
        
        except Exception as e:
            result.errors.append(f"采集失败: {str(e)}")
        
        return result
    
    def _get_source_files(self) -> List[Path]:
        """获取所有源代码文件"""
        files = []
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java'
        }
        
        for ext, lang in ext_to_lang.items():
            if lang in self.languages:
                for file_path in self.source_path.rglob(f"*{ext}"):
                    if not self._should_exclude(file_path):
                        files.append(file_path)
        
        return files
    
    def _should_exclude(self, file_path: Path) -> bool:
        """检查文件是否应该被排除"""
        path_str = str(file_path)
        for pattern in self.exclude_patterns:
            if pattern in path_str:
                return True
        return False
    
    def _collect_file(self, file_path: Path, project_id: str) -> CollectionResult:
        """采集单个文件的元数据"""
        result = CollectionResult()
        
        try:
            lang = self._detect_language(file_path)
            if not lang:
                return result
            
            # 创建文件实体
            file_entity = self.create_entity(
                entity_type="CodeFile",
                name=file_path.name,
                description=f"源代码文件: {file_path}",
                properties={
                    "path": str(file_path),
                    "language": lang,
                    "extension": file_path.suffix
                }
            )
            result.entities.append(file_entity)
            
            # 创建项目包含文件的关系
            contains_rel = self.create_relationship(
                project_id,
                file_entity.id,
                "CONTAINS"
            )
            result.relationships.append(contains_rel)
            
            # 文件属于项目（BELONGS_TO关系）
            belongs_to_rel = self.create_relationship(
                file_entity.id,
                project_id,
                "BELONGS_TO"
            )
            result.relationships.append(belongs_to_rel)
            
            # 根据语言类型采集
            if lang == 'python':
                python_result = self._collect_python_file(file_path, file_entity.id)
                result.entities.extend(python_result.entities)
                result.relationships.extend(python_result.relationships)
            elif lang in ['javascript', 'typescript']:
                js_result = self._collect_js_file(file_path, file_entity.id)
                result.entities.extend(js_result.entities)
                result.relationships.extend(js_result.relationships)
            elif lang == 'java':
                java_result = self._collect_java_file(file_path, file_entity.id)
                result.entities.extend(java_result.entities)
                result.relationships.extend(java_result.relationships)
        
        except Exception as e:
            result.errors.append(f"采集文件 {file_path} 失败: {str(e)}")
        
        return result
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """检测文件语言"""
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java'
        }
        return ext_to_lang.get(file_path.suffix)
    
    def _collect_python_file(self, file_path: Path, file_id: str) -> CollectionResult:
        """采集 Python 文件元数据"""
        result = CollectionResult()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_entity = self.create_entity(
                        entity_type="CodeFunction",
                        name=node.name,
                        description=f"函数: {node.name}",
                        properties={
                            "line_number": node.lineno,
                            "parameters": [arg.arg for arg in node.args.args],
                            "language": "python"
                        }
                    )
                    result.entities.append(func_entity)
                    
                    # 文件包含函数
                    contains_rel = self.create_relationship(
                        file_id,
                        func_entity.id,
                        "CONTAINS"
                    )
                    result.relationships.append(contains_rel)
                    
                    # 函数属于文件（BELONGS_TO关系）
                    belongs_to_rel = self.create_relationship(
                        func_entity.id,
                        file_id,
                        "BELONGS_TO"
                    )
                    result.relationships.append(belongs_to_rel)
                
                elif isinstance(node, ast.ClassDef):
                    class_entity = self.create_entity(
                        entity_type="CodeClass",
                        name=node.name,
                        description=f"类: {node.name}",
                        properties={
                            "line_number": node.lineno,
                            "bases": [ast.unparse(b) for b in node.bases] if hasattr(ast, 'unparse') else [],
                            "language": "python"
                        }
                    )
                    result.entities.append(class_entity)
                    
                    # 文件包含类
                    contains_rel = self.create_relationship(
                        file_id,
                        class_entity.id,
                        "CONTAINS"
                    )
                    result.relationships.append(contains_rel)
                    
                    # 类属于文件（BELONGS_TO关系）
                    belongs_to_rel = self.create_relationship(
                        class_entity.id,
                        file_id,
                        "BELONGS_TO"
                    )
                    result.relationships.append(belongs_to_rel)
                    
                    # 处理继承关系（INHERITS）
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_name = base.id
                            # 查找父类实体（如果已存在）
                            # 注意：这里假设父类在同一项目中，实际可能需要更复杂的查找逻辑
                            # 为了简化，我们创建父类实体（如果不存在）
                            parent_class = self.create_entity(
                                entity_type="CodeClass",
                                name=base_name,
                                description=f"父类: {base_name}",
                                properties={
                                    "language": "python",
                                    "is_reference": True  # 标记为引用，可能不在当前文件中
                                }
                            )
                            result.entities.append(parent_class)
                            
                            inherits_rel = self.create_relationship(
                                class_entity.id,
                                parent_class.id,
                                "INHERITS"
                            )
                            result.relationships.append(inherits_rel)
                
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        module_entity = self.create_entity(
                            entity_type="CodeModule",
                            name=node.module,
                            description=f"导入模块: {node.module}",
                            properties={}
                        )
                        result.entities.append(module_entity)
                        
                        imports_rel = self.create_relationship(
                            file_id,
                            module_entity.id,
                            "IMPORTS"
                        )
                        result.relationships.append(imports_rel)
        
        except Exception as e:
            result.errors.append(f"解析 Python 文件失败: {str(e)}")
        
        return result
    
    def _collect_js_file(self, file_path: Path, file_id: str) -> CollectionResult:
        """采集 JavaScript/TypeScript 文件元数据"""
        result = CollectionResult()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lang = 'typescript' if file_path.suffix == '.ts' else 'javascript'
            
            # 提取导入语句
            import_pattern = r'(?:import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+)?["\']([^"\']+)["\']|require\s*\(\s*["\']([^"\']+)["\']\s*\))'
            for match in re.finditer(import_pattern, content):
                module_name = match.group(1) or match.group(2)
                if module_name:
                    module_entity = self.create_entity(
                        entity_type="CodeModule",
                        name=module_name,
                        description=f"导入模块: {module_name}",
                        properties={
                            "import_path": module_name
                        }
                    )
                    result.entities.append(module_entity)
                    
                    imports_rel = self.create_relationship(
                        file_id,
                        module_entity.id,
                        "IMPORTS"
                    )
                    result.relationships.append(imports_rel)
            
            # 提取类定义
            class_pattern = r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?\s*\{'
            for match in re.finditer(class_pattern, content):
                class_name = match.group(1)
                extends = match.group(2)
                implements = match.group(3)
                
                # 获取类定义的行号
                line_num = content[:match.start()].count('\n') + 1
                
                bases = []
                if extends:
                    bases.append(extends)
                
                is_interface = 'interface' in match.group(0) if match.group(0) else False
                
                class_entity = self.create_entity(
                    entity_type="CodeClass",
                    name=class_name,
                    description=f"类: {class_name}",
                    properties={
                        "line_number": line_num,
                        "bases": bases,
                        "language": lang,
                        "is_interface": is_interface
                    }
                )
                result.entities.append(class_entity)
                
                # 文件包含类
                contains_rel = self.create_relationship(
                    file_id,
                    class_entity.id,
                    "CONTAINS"
                )
                result.relationships.append(contains_rel)
                
                # 类属于文件（BELONGS_TO关系）
                belongs_to_rel = self.create_relationship(
                    class_entity.id,
                    file_id,
                    "BELONGS_TO"
                )
                result.relationships.append(belongs_to_rel)
                
                # 处理继承关系（INHERITS）
                if extends:
                    parent_class = self.create_entity(
                        entity_type="CodeClass",
                        name=extends,
                        description=f"父类: {extends}",
                        properties={
                            "language": lang,
                            "is_reference": True
                        }
                    )
                    result.entities.append(parent_class)
                    
                    inherits_rel = self.create_relationship(
                        class_entity.id,
                        parent_class.id,
                        "INHERITS"
                    )
                    result.relationships.append(inherits_rel)
            
            # 提取接口定义（TypeScript）
            if lang == 'typescript':
                interface_pattern = r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([^{]+))?\s*\{'
                for match in re.finditer(interface_pattern, content):
                    interface_name = match.group(1)
                    extends = match.group(2)
                    
                    line_num = content[:match.start()].count('\n') + 1
                    
                    bases = []
                    if extends:
                        bases.extend([b.strip() for b in extends.split(',')])
                    
                    interface_entity = self.create_entity(
                        entity_type="CodeClass",
                        name=interface_name,
                        description=f"接口: {interface_name}",
                        properties={
                            "line_number": line_num,
                            "bases": bases,
                            "language": lang,
                            "is_interface": True
                        }
                    )
                    result.entities.append(interface_entity)
                    
                    # 文件包含接口
                    contains_rel = self.create_relationship(
                        file_id,
                        interface_entity.id,
                        "CONTAINS"
                    )
                    result.relationships.append(contains_rel)
                    
                    # 接口属于文件（BELONGS_TO关系）
                    belongs_to_rel = self.create_relationship(
                        interface_entity.id,
                        file_id,
                        "BELONGS_TO"
                    )
                    result.relationships.append(belongs_to_rel)
                    
                    # 处理接口继承关系（INHERITS）
                    if extends:
                        parent_interface = self.create_entity(
                            entity_type="CodeClass",
                            name=extends.strip(),
                            description=f"父接口: {extends.strip()}",
                            properties={
                                "language": lang,
                                "is_interface": True,
                                "is_reference": True
                            }
                        )
                        result.entities.append(parent_interface)
                        
                        inherits_rel = self.create_relationship(
                            interface_entity.id,
                            parent_interface.id,
                            "INHERITS"
                        )
                        result.relationships.append(inherits_rel)
            
            # 提取函数定义（包括箭头函数、普通函数、方法）
            # 普通函数和箭头函数
            function_patterns = [
                r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
                r'(?:export\s+)?(?:async\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>',
                r'(?:export\s+)?(?:async\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?function\s*\(([^)]*)\)'
            ]
            
            for pattern in function_patterns:
                for match in re.finditer(pattern, content):
                    func_name = match.group(1)
                    params_str = match.group(2) if len(match.groups()) > 1 else ""
                    
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # 解析参数
                    params = []
                    if params_str:
                        params = [p.strip().split(':')[0].split('=')[0].strip() 
                                 for p in params_str.split(',') if p.strip()]
                    
                    is_async = 'async' in match.group(0)
                    
                    func_entity = self.create_entity(
                        entity_type="CodeFunction",
                        name=func_name,
                        description=f"函数: {func_name}",
                        properties={
                            "line_number": line_num,
                            "parameters": params,
                            "language": lang,
                            "is_async": is_async
                        }
                    )
                    result.entities.append(func_entity)
                    
                    # 文件包含函数
                    contains_rel = self.create_relationship(
                        file_id,
                        func_entity.id,
                        "CONTAINS"
                    )
                    result.relationships.append(contains_rel)
                    
                    # 函数属于文件（BELONGS_TO关系）
                    belongs_to_rel = self.create_relationship(
                        func_entity.id,
                        file_id,
                        "BELONGS_TO"
                    )
                    result.relationships.append(belongs_to_rel)
            
            # 提取类方法
            method_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\s*\{'
            for match in re.finditer(method_pattern, content):
                method_name = match.group(1)
                # 跳过构造函数
                if method_name in ['constructor', 'get', 'set']:
                    continue
                
                params_str = match.group(2) if len(match.groups()) > 1 else ""
                
                line_num = content[:match.start()].count('\n') + 1
                
                params = []
                if params_str:
                    params = [p.strip().split(':')[0].split('=')[0].strip() 
                             for p in params_str.split(',') if p.strip()]
                
                is_async = 'async' in match.group(0)
                is_static = 'static' in match.group(0)
                
                func_entity = self.create_entity(
                    entity_type="CodeFunction",
                    name=method_name,
                    description=f"方法: {method_name}",
                    properties={
                        "line_number": line_num,
                        "parameters": params,
                        "language": lang,
                        "is_async": is_async,
                        "is_static": is_static
                    }
                )
                result.entities.append(func_entity)
                
                # 文件包含方法
                contains_rel = self.create_relationship(
                    file_id,
                    func_entity.id,
                    "CONTAINS"
                )
                result.relationships.append(contains_rel)
                
                # 方法属于文件（BELONGS_TO关系）
                belongs_to_rel = self.create_relationship(
                    func_entity.id,
                    file_id,
                    "BELONGS_TO"
                )
                result.relationships.append(belongs_to_rel)
        
        except Exception as e:
            result.errors.append(f"解析 JavaScript/TypeScript 文件失败: {str(e)}")
        
        return result
    
    def _collect_java_file(self, file_path: Path, file_id: str) -> CollectionResult:
        """采集 Java 文件元数据"""
        result = CollectionResult()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取导入语句
            import_pattern = r'import\s+(?:static\s+)?([\w.]+)(?:\.\*)?\s*;'
            for match in re.finditer(import_pattern, content):
                module_name = match.group(1)
                if module_name:
                    module_entity = self.create_entity(
                        entity_type="CodeModule",
                        name=module_name,
                        description=f"导入包: {module_name}",
                        properties={
                            "import_path": module_name
                        }
                    )
                    result.entities.append(module_entity)
                    
                    imports_rel = self.create_relationship(
                        file_id,
                        module_entity.id,
                        "IMPORTS"
                    )
                    result.relationships.append(imports_rel)
            
            # 提取类定义
            class_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?(?:final\s+)?(?:class|interface|enum)\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?\s*\{'
            for match in re.finditer(class_pattern, content):
                class_name = match.group(1)
                extends = match.group(2)
                implements = match.group(3)
                
                line_num = content[:match.start()].count('\n') + 1
                
                bases = []
                if extends:
                    bases.append(extends)
                
                is_interface = 'interface' in match.group(0)
                is_enum = 'enum' in match.group(0)
                
                class_entity = self.create_entity(
                    entity_type="CodeClass",
                    name=class_name,
                    description=f"类: {class_name}",
                    properties={
                        "line_number": line_num,
                        "bases": bases,
                        "language": "java",
                        "is_interface": is_interface,
                        "is_enum": is_enum
                    }
                )
                result.entities.append(class_entity)
                
                # 文件包含类
                contains_rel = self.create_relationship(
                    file_id,
                    class_entity.id,
                    "CONTAINS"
                )
                result.relationships.append(contains_rel)
                
                # 类属于文件（BELONGS_TO关系）
                belongs_to_rel = self.create_relationship(
                    class_entity.id,
                    file_id,
                    "BELONGS_TO"
                )
                result.relationships.append(belongs_to_rel)
                
                # 处理继承关系（INHERITS）
                if extends:
                    parent_class = self.create_entity(
                        entity_type="CodeClass",
                        name=extends,
                        description=f"父类: {extends}",
                        properties={
                            "language": "java",
                            "is_reference": True
                        }
                    )
                    result.entities.append(parent_class)
                    
                    inherits_rel = self.create_relationship(
                        class_entity.id,
                        parent_class.id,
                        "INHERITS"
                    )
                    result.relationships.append(inherits_rel)
                
                # 如果实现了接口，提取接口列表
                if implements:
                    interface_list = [i.strip() for i in implements.split(',')]
                    for interface_name in interface_list:
                        # 创建接口实体
                        interface_entity = self.create_entity(
                            entity_type="CodeClass",
                            name=interface_name,
                            description=f"接口: {interface_name}",
                            properties={
                                "language": lang,
                                "is_interface": True,
                                "is_reference": True
                            }
                        )
                        result.entities.append(interface_entity)
                        
                        # 创建实现关系（IMPLEMENTS）
                        implements_rel = self.create_relationship(
                            class_entity.id,
                            interface_entity.id,
                            "IMPLEMENTS"
                        )
                        result.relationships.append(implements_rel)
            
            # 提取方法定义
            method_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:abstract\s+)?(?:final\s+)?(?:synchronized\s+)?(?:<[^>]+>\s+)?(?:[\w.<>\[\]]+\s+)?(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w\s,]+)?\s*\{'
            for match in re.finditer(method_pattern, content):
                method_name = match.group(1)
                # 跳过构造函数（方法名与类名相同的情况需要额外判断）
                params_str = match.group(2) if len(match.groups()) > 1 else ""
                
                line_num = content[:match.start()].count('\n') + 1
                
                # 解析参数
                params = []
                if params_str:
                    # 处理参数，格式如: String name, int age
                    param_parts = params_str.split(',')
                    for param in param_parts:
                        param = param.strip()
                        if param:
                            # 提取参数名（最后一个单词）
                            parts = param.split()
                            if len(parts) > 0:
                                param_name = parts[-1]
                                params.append(param_name)
                
                is_static = 'static' in match.group(0)
                is_constructor = method_name and method_name[0].isupper()  # 简单判断，构造函数通常首字母大写
                
                func_entity = self.create_entity(
                    entity_type="CodeFunction",
                    name=method_name,
                    description=f"方法: {method_name}",
                    properties={
                        "line_number": line_num,
                        "parameters": params,
                        "language": "java",
                        "is_static": is_static,
                        "is_constructor": is_constructor
                    }
                )
                result.entities.append(func_entity)
                
                # 文件包含方法
                contains_rel = self.create_relationship(
                    file_id,
                    func_entity.id,
                    "CONTAINS"
                )
                result.relationships.append(contains_rel)
                
                # 方法属于文件（BELONGS_TO关系）
                belongs_to_rel = self.create_relationship(
                    func_entity.id,
                    file_id,
                    "BELONGS_TO"
                )
                result.relationships.append(belongs_to_rel)
        
        except Exception as e:
            result.errors.append(f"解析 Java 文件失败: {str(e)}")
        
        return result
