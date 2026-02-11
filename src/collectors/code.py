"""
编程语言代码元数据采集器
支持 Python, JavaScript, Java, TypeScript 等
"""
import os
import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import tree_sitter
from tree_sitter import Language, Parser

from .base import BaseCollector
from ..core.models import (
    CollectionResult,
    MetadataType,
    RelationshipType
)


class CodeMetadataCollector(BaseCollector):
    """代码元数据采集器"""
    
    # 支持的语言
    SUPPORTED_LANGUAGES = {
        'python': 'tree_sitter_python',
        'javascript': 'tree_sitter_javascript',
        'typescript': 'tree_sitter_typescript',
        'java': 'tree_sitter_java'
    }
    
    def __init__(self, source_path: str, source: str, 
                 languages: Optional[List[str]] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化代码采集器
        
        Args:
            source_path: 源代码路径
            source: 数据源标识
            languages: 支持的语言列表
            config: 配置信息
        """
        super().__init__("code_metadata", source, config)
        self.source_path = Path(source_path)
        self.languages = languages or ['python']
        self.exclude_patterns = self.get_config('exclude_patterns', [])
        self.parsers = {}
        self._init_parsers()
        print(f"初始化硬编码解析器进行采集代码元数据")
    
    def _init_parsers(self):
        """初始化语言解析器"""
        for lang in self.languages:
            if lang in self.SUPPORTED_LANGUAGES:
                try:
                    # 这里需要根据实际的 tree-sitter 语言绑定来初始化
                    # 示例代码，实际使用时需要正确配置
                    parser = Parser()
                    # parser.set_language(Language(self.SUPPORTED_LANGUAGES[lang], lang))
                    self.parsers[lang] = parser
                except Exception as e:
                    print(f"初始化 {lang} 解析器失败: {e}")
    
    def collect(self) -> CollectionResult:
        """
        采集代码元数据
        
        Returns:
            采集结果
        """
        result = CollectionResult()
        
        try:
            # 创建项目实体
            project_entity = self.create_entity(
                MetadataType.DIRECTORY,
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
        
        # 文件扩展名映射
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java'
        }
        
        for ext, lang in ext_to_lang.items():
            if lang in self.languages:
                for file_path in self.source_path.rglob(f"*{ext}"):
                    # 检查排除模式
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
            # 确定文件语言
            lang = self._detect_language(file_path)
            if not lang:
                return result
            
            # 创建文件实体
            file_entity = self.create_entity(
                MetadataType.FILE,
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
                RelationshipType.CONTAINS
            )
            result.relationships.append(contains_rel)
            
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
            
            # 采集模块级别的定义
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_entity = self.create_entity(
                        MetadataType.FUNCTION,
                        name=node.name,
                        description=f"函数: {node.name}",
                        properties={
                            "line_number": node.lineno,
                            "args": [arg.arg for arg in node.args.args],
                            "decorators": [ast.unparse(d) for d in node.decorator_list] if hasattr(ast, 'unparse') else []
                        }
                    )
                    result.entities.append(func_entity)
                    
                    # 创建文件包含函数的关系
                    contains_rel = self.create_relationship(
                        file_id,
                        func_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
                
                elif isinstance(node, ast.ClassDef):
                    class_entity = self.create_entity(
                        MetadataType.CLASS,
                        name=node.name,
                        description=f"类: {node.name}",
                        properties={
                            "line_number": node.lineno,
                            "bases": [ast.unparse(b) for b in node.bases] if hasattr(ast, 'unparse') else [],
                            "decorators": [ast.unparse(d) for d in node.decorator_list] if hasattr(ast, 'unparse') else []
                        }
                    )
                    result.entities.append(class_entity)
                    
                    # 创建文件包含类的关系
                    contains_rel = self.create_relationship(
                        file_id,
                        class_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
                
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    # 处理导入关系
                    if isinstance(node, ast.ImportFrom) and node.module:
                        import_entity = self.create_entity(
                            MetadataType.MODULE,
                            name=node.module,
                            description=f"导入模块: {node.module}",
                            properties={}
                        )
                        result.entities.append(import_entity)
                        
                        # 创建导入关系
                        imports_rel = self.create_relationship(
                            file_id,
                            import_entity.id,
                            RelationshipType.IMPORTS
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
            
            lines = content.split('\n')
            is_typescript = file_path.suffix == '.ts' or file_path.suffix == '.tsx'
            
            # 提取类定义（ES6 class）
            class_pattern = r'(?:export\s+)?(?:abstract\s+)?(?:default\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?'
            
            # 提取函数声明 function name() {}
            function_decl_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)'
            
            # 提取函数表达式 const name = function() {} 或 const name = () => {}
            function_expr_pattern = r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:function\s*\(|\([^)]*\)\s*=>)'
            
            # 提取箭头函数 const name = () => {}
            arrow_function_pattern = r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'
            
            # 提取方法定义（类中的方法）
            method_pattern = r'(?:public|private|protected|static|async|\s)*\s*(\w+)\s*\([^)]*\)\s*(?:\{|:|\s*=>)'
            
            # 提取TypeScript接口定义
            interface_pattern = r'(?:export\s+)?(?:default\s+)?interface\s+(\w+)'
            
            # 提取TypeScript类型定义
            type_pattern = r'(?:export\s+)?(?:type|type\s+alias)\s+(\w+)'
            
            # 提取导入语句
            import_pattern = r'import\s+(?:(?:\*\s+as\s+(\w+))|(?:\{([^}]+)\})|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]'
            
            # 提取导出语句
            export_pattern = r'export\s+(?:(?:default\s+)?(?:class|function|const|let|var|interface|type)\s+(\w+)|(?:\{([^}]+)\})|(?:\*\s+from\s+[\'"]([^\'"]+)[\'"]))'
            
            current_class = None
            current_class_id = None
            brace_count = 0
            paren_count = 0
            in_class = False
            in_function = False
            function_brace_count = 0
            
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                
                # 跳过注释和空行
                if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                    continue
                
                # 计算大括号和小括号以跟踪作用域
                brace_count += line.count('{') - line.count('}')
                paren_count += line.count('(') - line.count(')')
                
                # 检查类定义
                class_match = re.search(class_pattern, line)
                if class_match and not in_class:
                    class_name = class_match.group(1)
                    extends_class = class_match.group(2) if class_match.group(2) else None
                    implements_interfaces = class_match.group(3) if class_match.group(3) else None
                    
                    class_entity = self.create_entity(
                        MetadataType.CLASS,
                        name=class_name,
                        description=f"JavaScript/TypeScript类: {class_name}",
                        properties={
                            "line_number": line_num,
                            "extends": extends_class,
                            "implements": implements_interfaces.split(',') if implements_interfaces else [],
                            "file": str(file_path),
                            "is_typescript": is_typescript
                        }
                    )
                    result.entities.append(class_entity)
                    
                    # 创建文件包含类的关系
                    contains_rel = self.create_relationship(
                        file_id,
                        class_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
                    
                    # 如果有继承关系
                    if extends_class:
                        extends_entity = self.create_entity(
                            MetadataType.CLASS,
                            name=extends_class,
                            description=f"父类: {extends_class}",
                            properties={}
                        )
                        result.entities.append(extends_entity)
                        inherits_rel = self.create_relationship(
                            class_entity.id,
                            extends_entity.id,
                            RelationshipType.INHERITS
                        )
                        result.relationships.append(inherits_rel)
                    
                    current_class = class_name
                    current_class_id = class_entity.id
                    in_class = True
                    brace_count = 0
                
                # 检查TypeScript接口定义
                if is_typescript:
                    interface_match = re.search(interface_pattern, line)
                    if interface_match and not in_class:
                        interface_name = interface_match.group(1)
                        interface_entity = self.create_entity(
                            MetadataType.CLASS,  # 使用CLASS类型表示接口
                            name=interface_name,
                            description=f"TypeScript接口: {interface_name}",
                            properties={
                                "line_number": line_num,
                                "is_interface": True,
                                "file": str(file_path)
                            }
                        )
                        result.entities.append(interface_entity)
                        
                        contains_rel = self.create_relationship(
                            file_id,
                            interface_entity.id,
                            RelationshipType.CONTAINS
                        )
                        result.relationships.append(contains_rel)
                    
                    # 检查TypeScript类型定义
                    type_match = re.search(type_pattern, line)
                    if type_match and not in_class:
                        type_name = type_match.group(1)
                        type_entity = self.create_entity(
                            MetadataType.CLASS,  # 使用CLASS类型表示类型
                            name=type_name,
                            description=f"TypeScript类型: {type_name}",
                            properties={
                                "line_number": line_num,
                                "is_type": True,
                                "file": str(file_path)
                            }
                        )
                        result.entities.append(type_entity)
                        
                        contains_rel = self.create_relationship(
                            file_id,
                            type_entity.id,
                            RelationshipType.CONTAINS
                        )
                        result.relationships.append(contains_rel)
                
                # 检查函数声明 function name() {}
                function_decl_match = re.search(function_decl_pattern, line)
                if function_decl_match and not in_class and not in_function:
                    func_name = function_decl_match.group(1)
                    
                    # 提取参数
                    param_match = re.search(r'\(([^)]*)\)', line)
                    params = []
                    if param_match:
                        param_str = param_match.group(1)
                        if param_str.strip():
                            for param in param_str.split(','):
                                param = param.strip()
                                if param:
                                    # 处理默认参数和类型注解
                                    param_name = param.split('=')[0].split(':')[0].strip()
                                    param_type = None
                                    if ':' in param:
                                        param_type = param.split(':')[1].split('=')[0].strip()
                                    params.append({
                                        "name": param_name,
                                        "type": param_type
                                    })
                    
                    func_entity = self.create_entity(
                        MetadataType.FUNCTION,
                        name=func_name,
                        description=f"函数: {func_name}",
                        properties={
                            "line_number": line_num,
                            "parameters": params,
                            "file": str(file_path),
                            "is_async": "async" in line,
                            "is_typescript": is_typescript
                        }
                    )
                    result.entities.append(func_entity)
                    
                    # 创建文件包含函数的关系
                    contains_rel = self.create_relationship(
                        file_id,
                        func_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
                    
                    in_function = True
                    function_brace_count = brace_count
                
                # 检查函数表达式和箭头函数
                function_expr_match = re.search(function_expr_pattern, line) or re.search(arrow_function_pattern, line)
                if function_expr_match and not in_class and not in_function:
                    func_name = function_expr_match.group(1)
                    
                    # 跳过明显不是函数的变量（如对象、数组等）
                    if re.search(r'=\s*[\[{]', line):
                        continue
                    
                    # 提取参数
                    param_match = re.search(r'\(([^)]*)\)', line)
                    params = []
                    if param_match:
                        param_str = param_match.group(1)
                        if param_str.strip():
                            for param in param_str.split(','):
                                param = param.strip()
                                if param:
                                    param_name = param.split('=')[0].split(':')[0].strip()
                                    param_type = None
                                    if ':' in param:
                                        param_type = param.split(':')[1].split('=')[0].strip()
                                    params.append({
                                        "name": param_name,
                                        "type": param_type
                                    })
                    
                    func_entity = self.create_entity(
                        MetadataType.FUNCTION,
                        name=func_name,
                        description=f"函数表达式: {func_name}",
                        properties={
                            "line_number": line_num,
                            "parameters": params,
                            "file": str(file_path),
                            "is_arrow_function": "=>" in line,
                            "is_async": "async" in line,
                            "is_typescript": is_typescript
                        }
                    )
                    result.entities.append(func_entity)
                    
                    # 创建文件包含函数的关系
                    contains_rel = self.create_relationship(
                        file_id,
                        func_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
                
                # 检查类中的方法定义
                if in_class and brace_count > 0:
                    # 排除构造函数和getter/setter
                    if re.search(r'constructor\s*\(', line) or re.search(r'(?:get|set)\s+\w+\s*\(', line):
                        continue
                    
                    method_match = re.search(method_pattern, line)
                    if method_match:
                        method_name = method_match.group(1)
                        
                        # 跳过一些关键字
                        if method_name in ['if', 'for', 'while', 'switch', 'catch', 'try', 'return', 'new', 'this', 'super', 'async', 'await']:
                            continue
                        
                        # 提取参数
                        param_match = re.search(r'\(([^)]*)\)', line)
                        params = []
                        if param_match:
                            param_str = param_match.group(1)
                            if param_str.strip():
                                for param in param_str.split(','):
                                    param = param.strip()
                                    if param:
                                        param_name = param.split('=')[0].split(':')[0].strip()
                                        param_type = None
                                        if ':' in param:
                                            param_type = param.split(':')[1].split('=')[0].strip()
                                        params.append({
                                            "name": param_name,
                                            "type": param_type
                                        })
                        
                        method_entity = self.create_entity(
                            MetadataType.FUNCTION,
                            name=method_name,
                            description=f"方法: {method_name}",
                            properties={
                                "line_number": line_num,
                                "parameters": params,
                                "class": current_class,
                                "file": str(file_path),
                                "is_async": "async" in line,
                                "is_static": "static" in line,
                                "is_typescript": is_typescript
                            }
                        )
                        result.entities.append(method_entity)
                        
                        # 创建类包含方法的关系
                        if current_class_id:
                            contains_rel = self.create_relationship(
                                current_class_id,
                                method_entity.id,
                                RelationshipType.CONTAINS
                            )
                            result.relationships.append(contains_rel)
                
                # 检查导入语句
                import_match = re.search(import_pattern, line)
                if import_match:
                    module_name = import_match.group(4) if import_match.group(4) else None
                    if module_name:
                        import_entity = self.create_entity(
                            MetadataType.MODULE,
                            name=module_name,
                            description=f"导入模块: {module_name}",
                            properties={
                                "line_number": line_num,
                                "file": str(file_path)
                            }
                        )
                        result.entities.append(import_entity)
                        
                        # 创建导入关系
                        imports_rel = self.create_relationship(
                            file_id,
                            import_entity.id,
                            RelationshipType.IMPORTS
                        )
                        result.relationships.append(imports_rel)
                
                # 检查导出语句（除了已经处理的类、函数等）
                export_match = re.search(export_pattern, line)
                if export_match and not class_match and not function_decl_match and not function_expr_match:
                    # 处理 export { ... } 或 export * from ...
                    exported_items = export_match.group(2) if export_match.group(2) else None
                    export_from = export_match.group(3) if export_match.group(3) else None
                    if exported_items:
                        # 解析导出的项目
                        for item in exported_items.split(','):
                            item = item.strip()
                            if item:
                                export_entity = self.create_entity(
                                    MetadataType.MODULE,
                                    name=item,
                                    description=f"导出: {item}",
                                    properties={
                                        "line_number": line_num,
                                        "file": str(file_path)
                                    }
                                )
                                result.entities.append(export_entity)
                    elif export_from:
                        # export * from 'module'
                        import_entity = self.create_entity(
                            MetadataType.MODULE,
                            name=export_from,
                            description=f"导出模块: {export_from}",
                            properties={
                                "line_number": line_num,
                                "file": str(file_path)
                            }
                        )
                        result.entities.append(import_entity)
                        
                        imports_rel = self.create_relationship(
                            file_id,
                            import_entity.id,
                            RelationshipType.IMPORTS
                        )
                        result.relationships.append(imports_rel)
                
                # 如果类的大括号闭合，重置状态
                if in_class and brace_count <= 0:
                    in_class = False
                    current_class = None
                    current_class_id = None
                
                # 如果函数的大括号闭合，重置状态
                if in_function and brace_count < function_brace_count:
                    in_function = False
                    function_brace_count = 0
            
        except Exception as e:
            result.errors.append(f"解析 JavaScript/TypeScript 文件失败: {str(e)}")
            import traceback
            result.errors.append(f"详细错误: {traceback.format_exc()}")
        
        return result
    
    def _collect_java_file(self, file_path: Path, file_id: str) -> CollectionResult:
        """采集 Java 文件元数据"""
        result = CollectionResult()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # 使用正则表达式提取类和方法
            # 提取类定义（包括public、private、protected、abstract等修饰符）
            class_pattern = r'(?:public|private|protected|abstract|final|static|\s)*\s*class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?'
            
            # 提取方法定义（包括构造函数）
            # 匹配方法签名：修饰符 + 返回类型 + 方法名 + 参数列表
            method_pattern = r'(?:public|private|protected|static|final|abstract|synchronized|native|\s)*\s*(?:(\w+(?:<[^>]+>)?(?:\s*\[\s*\])*)\s+)?(\w+)\s*\([^)]*\)\s*(?:\{|\s*throws\s+[\w\s,]+)?'
            
            # 提取接口定义
            interface_pattern = r'(?:public|private|protected|\s)*\s*interface\s+(\w+)'
            
            # 提取枚举定义
            enum_pattern = r'(?:public|private|protected|\s)*\s*enum\s+(\w+)'
            
            current_class = None
            current_class_id = None
            brace_count = 0
            in_class = False
            
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                
                # 跳过注释和空行
                if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                    continue
                
                # 计算大括号以跟踪类/方法的范围
                brace_count += line.count('{') - line.count('}')
                
                # 检查类定义
                class_match = re.search(class_pattern, line)
                if class_match and not in_class:
                    class_name = class_match.group(1)
                    extends_class = class_match.group(2) if class_match.group(2) else None
                    implements_interfaces = class_match.group(3) if class_match.group(3) else None
                    
                    class_entity = self.create_entity(
                        MetadataType.CLASS,
                        name=class_name,
                        description=f"Java类: {class_name}",
                        properties={
                            "line_number": line_num,
                            "extends": extends_class,
                            "implements": implements_interfaces.split(',') if implements_interfaces else [],
                            "file": str(file_path)
                        }
                    )
                    result.entities.append(class_entity)
                    
                    # 创建文件包含类的关系
                    contains_rel = self.create_relationship(
                        file_id,
                        class_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
                    
                    # 如果有继承关系
                    if extends_class:
                        # 创建继承关系（目标类可能不在当前文件中）
                        extends_entity = self.create_entity(
                            MetadataType.CLASS,
                            name=extends_class,
                            description=f"父类: {extends_class}",
                            properties={}
                        )
                        result.entities.append(extends_entity)
                        inherits_rel = self.create_relationship(
                            class_entity.id,
                            extends_entity.id,
                            RelationshipType.INHERITS
                        )
                        result.relationships.append(inherits_rel)
                    
                    current_class = class_name
                    current_class_id = class_entity.id
                    in_class = True
                    brace_count = 0
                
                # 检查接口定义
                interface_match = re.search(interface_pattern, line)
                if interface_match and not in_class:
                    interface_name = interface_match.group(1)
                    interface_entity = self.create_entity(
                        MetadataType.CLASS,  # 使用CLASS类型表示接口
                        name=interface_name,
                        description=f"Java接口: {interface_name}",
                        properties={
                            "line_number": line_num,
                            "is_interface": True,
                            "file": str(file_path)
                        }
                    )
                    result.entities.append(interface_entity)
                    
                    contains_rel = self.create_relationship(
                        file_id,
                        interface_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
                    
                    current_class = interface_name
                    current_class_id = interface_entity.id
                    in_class = True
                    brace_count = 0
                
                # 检查枚举定义
                enum_match = re.search(enum_pattern, line)
                if enum_match and not in_class:
                    enum_name = enum_match.group(1)
                    enum_entity = self.create_entity(
                        MetadataType.CLASS,  # 使用CLASS类型表示枚举
                        name=enum_name,
                        description=f"Java枚举: {enum_name}",
                        properties={
                            "line_number": line_num,
                            "is_enum": True,
                            "file": str(file_path)
                        }
                    )
                    result.entities.append(enum_entity)
                    
                    contains_rel = self.create_relationship(
                        file_id,
                        enum_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
                    
                    current_class = enum_name
                    current_class_id = enum_entity.id
                    in_class = True
                    brace_count = 0
                
                # 检查方法定义（只在类内部）
                if in_class and brace_count > 0:
                    # 更精确的方法匹配，排除类定义中的方法声明
                    # 排除一些明显不是方法的情况
                    if re.search(r'^\s*(?:if|for|while|switch|catch|try|return|new|this|super|assert|break|continue)\s*\(', line):
                        continue
                    
                    method_match = re.search(method_pattern, line)
                    if method_match:
                        return_type = method_match.group(1) if method_match.group(1) else None
                        method_name = method_match.group(2)
                        
                        # 跳过一些关键字和常见变量名
                        if method_name in ['if', 'for', 'while', 'switch', 'catch', 'try', 'return', 'new', 'this', 'super', 'assert', 'break', 'continue']:
                            continue
                        
                        # 跳过明显是变量赋值的情况（如：String name = ...）
                        if re.search(r'=\s*[^=]', line) and not re.search(r'\([^)]*\)\s*\{', line):
                            continue
                        
                        # 提取方法参数
                        param_match = re.search(r'\(([^)]*)\)', line)
                        params = []
                        if param_match:
                            param_str = param_match.group(1)
                            if param_str.strip():
                                # 简单解析参数（可能不完美，但基本可用）
                                for param in param_str.split(','):
                                    param = param.strip()
                                    if param:
                                        # 提取参数类型和名称
                                        param_parts = param.split()
                                        if len(param_parts) >= 2:
                                            params.append({
                                                "type": param_parts[0],
                                                "name": param_parts[-1]
                                            })
                        
                        # 检查是否是构造函数（方法名与类名相同）
                        is_constructor = (current_class and method_name == current_class)
                        
                        method_entity = self.create_entity(
                            MetadataType.FUNCTION,
                            name=method_name,
                            description=f"{'构造函数' if is_constructor else '方法'}: {method_name}",
                            properties={
                                "line_number": line_num,
                                "return_type": return_type if not is_constructor else None,
                                "is_constructor": is_constructor,
                                "parameters": params,
                                "class": current_class,
                                "file": str(file_path)
                            }
                        )
                        result.entities.append(method_entity)
                        
                        # 创建类包含方法的关系
                        if current_class_id:
                            contains_rel = self.create_relationship(
                                current_class_id,
                                method_entity.id,
                                RelationshipType.CONTAINS
                            )
                            result.relationships.append(contains_rel)
                        else:
                            # 如果没有类，直接关联到文件
                            contains_rel = self.create_relationship(
                                file_id,
                                method_entity.id,
                                RelationshipType.CONTAINS
                            )
                            result.relationships.append(contains_rel)
                
                # 如果类的大括号闭合，重置状态
                if in_class and brace_count <= 0:
                    in_class = False
                    current_class = None
                    current_class_id = None
            
        except Exception as e:
            result.errors.append(f"解析 Java 文件失败: {str(e)}")
            import traceback
            result.errors.append(f"详细错误: {traceback.format_exc()}")
        
        return result





