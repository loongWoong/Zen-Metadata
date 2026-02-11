"""
元模型注册表
"""
from typing import Dict, Any, List, Optional, Type
from pathlib import Path
import yaml
import json
from datetime import datetime

from .metamodel import EntityMetaModel, RelationshipMetaModel, MetaModelPackage
from .plugin_loader import PluginLoader, PluginSecurityError
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.collectors.base import BaseCollector


class MetaRegistry:
    """元模型注册表"""
    
    def __init__(self, metamodels_dir: str = "metamodels", plugins_dir: str = "plugins"):
        """
        初始化元模型注册表
        
        Args:
            metamodels_dir: 元模型配置文件目录
            plugins_dir: 插件目录
        """
        self.metamodels_dir = Path(metamodels_dir)
        self.metamodels_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugin_loader = PluginLoader(plugins_dir)
        
        # 注册表
        self.entity_models: Dict[str, EntityMetaModel] = {}  # key: type@version
        self.relationship_models: Dict[str, RelationshipMetaModel] = {}  # key: type@version
        self.collectors: Dict[str, Type[BaseCollector]] = {}  # key: entity_type
        
        # 版本管理
        self.entity_type_versions: Dict[str, List[str]] = {}  # type -> [versions]
        self.relationship_type_versions: Dict[str, List[str]] = {}  # type -> [versions]
        
        # 包管理：包名 -> 包信息
        self.packages: Dict[str, Dict[str, Any]] = {}  # package_name -> package_info
        
        # 采集器类型映射：collector_type -> entity_type（用于从采集器类型查找实体类型）
        self.collector_type_map: Dict[str, str] = {}  # collector_type -> entity_type
        # 实体类型到采集器类型的反向映射
        self.entity_to_collector_type: Dict[str, str] = {}  # entity_type -> collector_type
    
    def register_entity_model(self, model: EntityMetaModel, reload_plugin: bool = True, package_name: Optional[str] = None) -> bool:
        """
        注册实体元模型
        
        Args:
            model: 实体元模型
            reload_plugin: 是否重新加载插件
            package_name: 包名（用于查找包内的插件）
            
        Returns:
            是否成功
        """
        try:
            full_type = model.get_full_type()
            
            # 记录版本
            if model.type not in self.entity_type_versions:
                self.entity_type_versions[model.type] = []
            if model.version not in self.entity_type_versions[model.type]:
                self.entity_type_versions[model.type].append(model.version)
            
            # 注册模型
            self.entity_models[full_type] = model
            
            # 加载采集器插件（支持从包文件夹加载）
            if model.collector and reload_plugin:
                plugin_name = model.collector.get("plugin", "").replace(".py", "")
                if plugin_name:
                    collector_class = None
                    
                    # 优先从包文件夹加载插件
                    if package_name:
                        package_dir = self.metamodels_dir / package_name
                        package_plugin_file = package_dir / "plugins" / f"{plugin_name}.py"
                        if package_plugin_file.exists():
                            try:
                                collector_class = self.plugin_loader.load_plugin_from_file(package_plugin_file)
                            except Exception as e:
                                print(f"从包文件夹加载插件失败: {e}")
                    
                    # 如果包文件夹中没有，尝试从全局插件目录加载
                    if not collector_class:
                        plugin_file = self.plugin_loader.plugins_dir / f"{plugin_name}.py"
                        if plugin_file.exists():
                            try:
                                collector_class = self.plugin_loader.load_plugin_from_file(plugin_file)
                            except Exception as e:
                                print(f"从全局插件目录加载插件失败: {e}")
                    
                    if collector_class:
                        self.collectors[model.type] = collector_class
                        print(f"成功加载采集器插件: {plugin_name} for {model.type}")
                    else:
                        print(f"警告: 未找到采集器插件: {plugin_name} for {model.type}")
            
            return True
        except Exception as e:
            print(f"注册实体元模型失败: {e}")
            return False
    
    def register_relationship_model(self, model: RelationshipMetaModel) -> bool:
        """
        注册关系元模型
        
        Args:
            model: 关系元模型
            
        Returns:
            是否成功
        """
        try:
            full_type = model.get_full_type()
            
            # 记录版本
            if model.type not in self.relationship_type_versions:
                self.relationship_type_versions[model.type] = []
            if model.version not in self.relationship_type_versions[model.type]:
                self.relationship_type_versions[model.type].append(model.version)
            
            # 注册模型
            self.relationship_models[full_type] = model
            
            return True
        except Exception as e:
            print(f"注册关系元模型失败: {e}")
            return False
    
    def get_entity_model(self, entity_type: str, version: Optional[str] = None) -> Optional[EntityMetaModel]:
        """
        获取实体元模型
        
        Args:
            entity_type: 实体类型
            version: 版本号（如果为None，返回最新版本）
            
        Returns:
            实体元模型
        """
        if version:
            full_type = f"{entity_type}@{version}"
            return self.entity_models.get(full_type)
        else:
            # 返回最新版本
            versions = self.entity_type_versions.get(entity_type, [])
            if versions:
                # 简单版本比较（v1, v2, ...）
                latest_version = sorted(versions, key=lambda v: int(v[1:]) if v[1:].isdigit() else 0)[-1]
                full_type = f"{entity_type}@{latest_version}"
                return self.entity_models.get(full_type)
            return None
    
    def get_relationship_model(self, relationship_type: str, version: Optional[str] = None) -> Optional[RelationshipMetaModel]:
        """
        获取关系元模型
        
        Args:
            relationship_type: 关系类型
            version: 版本号（如果为None，返回最新版本）
            
        Returns:
            关系元模型
        """
        if version:
            full_type = f"{relationship_type}@{version}"
            return self.relationship_models.get(full_type)
        else:
            # 返回最新版本
            versions = self.relationship_type_versions.get(relationship_type, [])
            if versions:
                latest_version = sorted(versions, key=lambda v: int(v[1:]) if v[1:].isdigit() else 0)[-1]
                full_type = f"{relationship_type}@{latest_version}"
                return self.relationship_models.get(full_type)
            return None
    
    def get_collector(self, entity_type: str) -> Optional[Type[BaseCollector]]:
        """
        获取采集器类
        
        Args:
            entity_type: 实体类型
            
        Returns:
            采集器类
        """
        return self.collectors.get(entity_type)
    
    def load_from_file(self, file_path: Path) -> bool:
        """
        从文件加载元模型
        
        Args:
            file_path: 元模型文件路径
            
        Returns:
            是否成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix == '.yaml' or file_path.suffix == '.yml':
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # 检查数据是否为None或非字典类型
            if data is None:
                print(f"警告: 文件 {file_path} 为空或格式不正确")
                return False
            
            if not isinstance(data, dict):
                print(f"警告: 文件 {file_path} 的根元素不是字典，而是 {type(data).__name__}")
                return False
            
            # 尝试从文件路径推断包名
            package_name = None
            if file_path.parent != self.metamodels_dir:
                # 文件在子目录中，可能是包文件夹
                package_name = file_path.parent.name
            
            # 加载实体元模型（保存entity_models列表供后续使用）
            entity_models_list = data.get('entity_models', [])
            if 'entity_models' in data:
                if not isinstance(entity_models_list, list):
                    print(f"警告: 文件 {file_path} 中的 entity_models 不是列表")
                    return False
                
                for idx, model_data in enumerate(entity_models_list):
                    if not isinstance(model_data, dict):
                        print(f"警告: 文件 {file_path} 中第 {idx+1} 个实体元模型不是字典，而是 {type(model_data).__name__}: {model_data}")
                        continue
                    try:
                        model = EntityMetaModel(**model_data)
                        self.register_entity_model(model, reload_plugin=True, package_name=package_name)
                    except Exception as e:
                        print(f"警告: 加载实体元模型失败 (文件: {file_path}, 索引: {idx+1}): {e}")
                        continue
            
            # 加载关系元模型
            if 'relationship_models' in data:
                relationship_models = data['relationship_models']
                if not isinstance(relationship_models, list):
                    print(f"警告: 文件 {file_path} 中的 relationship_models 不是列表")
                    return False
                
                for idx, model_data in enumerate(relationship_models):
                    if not isinstance(model_data, dict):
                        print(f"警告: 文件 {file_path} 中第 {idx+1} 个关系元模型不是字典，而是 {type(model_data).__name__}: {model_data}")
                        continue
                    try:
                        model = RelationshipMetaModel(**model_data)
                        self.register_relationship_model(model)
                    except Exception as e:
                        print(f"警告: 加载关系元模型失败 (文件: {file_path}, 索引: {idx+1}): {e}")
                        continue
            
            # 加载插件
            if 'plugins' in data:
                for plugin_name, plugin_code in data['plugins'].items():
                    try:
                        # 保存到全局插件目录（向后兼容）
                        self.plugin_loader.save_plugin(plugin_code, plugin_name)
                        
                        # 如果文件在包文件夹中，同时保存到包文件夹
                        if package_name:
                            package_dir = self.metamodels_dir / package_name
                            package_plugins_dir = package_dir / "plugins"
                            package_plugins_dir.mkdir(parents=True, exist_ok=True)
                            plugin_file = package_plugins_dir / plugin_name
                            with open(plugin_file, 'w', encoding='utf-8') as f:
                                f.write(plugin_code)
                        
                        # 如果有关联的实体模型，加载插件
                        for entity_type, collector in self.collectors.items():
                            entity_model = self.get_entity_model(entity_type)
                            if entity_model and entity_model.collector:
                                if entity_model.collector.get("plugin", "").replace(".py", "") == plugin_name.replace(".py", ""):
                                    # 优先从包文件夹加载
                                    if package_name:
                                        package_plugin_file = self.metamodels_dir / package_name / "plugins" / plugin_name
                                        if package_plugin_file.exists():
                                            collector_class = self.plugin_loader.load_plugin_from_file(package_plugin_file)
                                        else:
                                            collector_class = self.plugin_loader.load_plugin_from_code(plugin_code, plugin_name.replace(".py", ""))
                                    else:
                                        collector_class = self.plugin_loader.load_plugin_from_code(plugin_code, plugin_name.replace(".py", ""))
                                    self.collectors[entity_type] = collector_class
                    except PluginSecurityError as e:
                        print(f"加载插件 {plugin_name} 失败（安全验证）: {e}")
            
            # 加载采集器类型和配置schema（从顶层字段或metadata）
            # 注意：必须在实体模型和插件加载完成后才能建立映射
            collector_type = data.get('collector_type')
            if not collector_type and isinstance(data.get('metadata'), dict):
                collector_type = data.get('metadata', {}).get('collector_type')
            
            # 加载配置schema（从顶层字段）
            config_schema = data.get('config_schema')
            
            if collector_type:
                # 从数据中的entity_models获取主要实体类型
                # 优先使用第一个有采集器的实体类型，如果没有则使用第一个实体类型
                primary_entity_type = None
                
                if isinstance(entity_models_list, list) and len(entity_models_list) > 0:
                    # 首先尝试找到有采集器的实体类型（插件已加载后）
                    for model_data in entity_models_list:
                        if isinstance(model_data, dict):
                            entity_type = model_data.get('type')
                            if entity_type and entity_type in self.collectors:
                                primary_entity_type = entity_type
                                break
                    
                    # 如果没有找到有采集器的，使用第一个实体类型（即使没有采集器也建立映射）
                    if not primary_entity_type:
                        first_model = entity_models_list[0]
                        if isinstance(first_model, dict):
                            primary_entity_type = first_model.get('type')
                
                if primary_entity_type:
                    self.collector_type_map[collector_type] = primary_entity_type
                    self.entity_to_collector_type[primary_entity_type] = collector_type
                    print(f"已注册采集器类型映射: {collector_type} -> {primary_entity_type} (文件: {file_path.name})")
                else:
                    print(f"警告: 无法为采集器类型 {collector_type} 找到对应的实体类型 (文件: {file_path.name})")
            
            return True
        except Exception as e:
            import traceback
            print(f"从文件加载元模型失败 {file_path}: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            return False
    
    def load_all(self):
        """加载所有元模型文件（支持包文件夹结构）"""
        if not self.metamodels_dir.exists():
            print(f"元模型目录不存在: {self.metamodels_dir}")
            return
        
        # 首先加载根目录下的文件（向后兼容）
        for file_path in self.metamodels_dir.glob("*.yaml"):
            if file_path.is_file():
                try:
                    self.load_from_file(file_path)
                except Exception as e:
                    print(f"加载文件失败 {file_path}: {e}")
        
        for file_path in self.metamodels_dir.glob("*.yml"):
            if file_path.is_file():
                try:
                    self.load_from_file(file_path)
                except Exception as e:
                    print(f"加载文件失败 {file_path}: {e}")
        
        for file_path in self.metamodels_dir.glob("*.json"):
            if file_path.is_file():
                try:
                    self.load_from_file(file_path)
                except Exception as e:
                    print(f"加载文件失败 {file_path}: {e}")
        
        # 打印已加载的采集器类型
        if self.collector_type_map:
            print(f"已加载的采集器类型映射 ({len(self.collector_type_map)} 个):")
            for collector_type, entity_type in self.collector_type_map.items():
                print(f"  - {collector_type} -> {entity_type}")
        else:
            print("警告: 未加载任何采集器类型映射")
        
        # 加载包文件夹中的文件
        for package_dir in self.metamodels_dir.iterdir():
            if package_dir.is_dir() and not package_dir.name.startswith('.'):
                package_name = package_dir.name
                package_info = {
                    "name": package_name,
                    "path": str(package_dir),
                    "entity_models": [],
                    "relationship_models": []
                }
                
                # 记录加载前的实体类型集合，用于后续识别新加载的实体
                entity_types_before = set(self.entity_models.keys())
                relationship_types_before = set(self.relationship_models.keys())
                
                # 用于保存从文件中读取的config_schema
                package_config_schema = None
                
                # 加载包内的元模型文件
                for file_path in package_dir.glob("*.yaml"):
                    if file_path.is_file() and file_path.name != "package_info.yaml":
                        try:
                            # 读取文件以获取config_schema
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_data = yaml.safe_load(f)
                                if file_data and isinstance(file_data, dict):
                                    # 如果文件中有config_schema，保存它（优先使用第一个找到的）
                                    if not package_config_schema and file_data.get('config_schema'):
                                        package_config_schema = file_data.get('config_schema')
                            
                            # 加载文件
                            self.load_from_file(file_path)
                        except Exception as e:
                            print(f"加载包文件失败 {file_path}: {e}")
                
                for file_path in package_dir.glob("*.yml"):
                    if file_path.is_file() and file_path.name != "package_info.yml":
                        try:
                            self.load_from_file(file_path)
                        except Exception as e:
                            print(f"加载包文件失败 {file_path}: {e}")
                
                for file_path in package_dir.glob("*.json"):
                    if file_path.is_file() and file_path.name != "package_info.json":
                        try:
                            self.load_from_file(file_path)
                        except Exception as e:
                            print(f"加载包文件失败 {file_path}: {e}")
                
                # 收集从该包加载的实体类型和关系类型
                entity_types_after = set(self.entity_models.keys())
                relationship_types_after = set(self.relationship_models.keys())
                
                # 找出新加载的实体类型（属于该包）
                new_entity_types = entity_types_after - entity_types_before
                for full_type in new_entity_types:
                    # 从 full_type (type@version) 中提取 type
                    entity_type = full_type.split('@')[0]
                    if entity_type not in package_info["entity_models"]:
                        package_info["entity_models"].append(entity_type)
                
                # 找出新加载的关系类型（属于该包）
                new_relationship_types = relationship_types_after - relationship_types_before
                for full_type in new_relationship_types:
                    # 从 full_type (type@version) 中提取 type
                    relationship_type = full_type.split('@')[0]
                    if relationship_type not in package_info["relationship_models"]:
                        package_info["relationship_models"].append(relationship_type)
                
                # 尝试从package_info.yaml加载包信息（会覆盖上面收集的信息，但保留collector_type等元数据）
                package_info_file = package_dir / "package_info.yaml"
                if package_info_file.exists():
                    try:
                        with open(package_info_file, 'r', encoding='utf-8') as f:
                            saved_info = yaml.safe_load(f)
                            if saved_info and isinstance(saved_info, dict):
                                # 更新包信息，但确保entity_models和relationship_models列表存在
                                if "entity_models" in saved_info and isinstance(saved_info["entity_models"], list):
                                    package_info["entity_models"] = saved_info["entity_models"]
                                if "relationship_models" in saved_info and isinstance(saved_info["relationship_models"], list):
                                    package_info["relationship_models"] = saved_info["relationship_models"]
                                # 更新其他字段（metadata, collector_type, config_schema等）
                                for key, value in saved_info.items():
                                    if key not in ["entity_models", "relationship_models"]:
                                        package_info[key] = value
                    except Exception as e:
                        print(f"加载包信息文件失败 {package_info_file}: {e}")
                
                # 如果从文件中读取到了config_schema但package_info中没有，则添加它
                if package_config_schema and "config_schema" not in package_info:
                    package_info["config_schema"] = package_config_schema
                
                # 如果包信息中有collector_type，建立映射（即使元模型文件本身没有collector_type字段）
                collector_type = package_info.get("collector_type")
                if collector_type and package_info.get("entity_models"):
                    # 从包的entity_models列表中选择主要实体类型
                    # 优先选择有采集器的实体类型
                    primary_entity_type = None
                    entity_types = package_info.get("entity_models", [])
                    
                    # 首先尝试找到有采集器的实体类型
                    for entity_type in entity_types:
                        if entity_type in self.collectors:
                            primary_entity_type = entity_type
                            break
                    
                    # 如果没有找到有采集器的，使用第一个实体类型
                    if not primary_entity_type and entity_types:
                        primary_entity_type = entity_types[0]
                    
                    # 建立映射（如果还没有建立的话）
                    if primary_entity_type:
                        if collector_type not in self.collector_type_map:
                            self.collector_type_map[collector_type] = primary_entity_type
                            self.entity_to_collector_type[primary_entity_type] = collector_type
                            print(f"已从package_info.yaml注册采集器类型映射: {collector_type} -> {primary_entity_type} (包: {package_name})")
                        elif self.collector_type_map[collector_type] != primary_entity_type:
                            # 如果映射已存在但指向不同的实体类型，更新它
                            old_entity_type = self.collector_type_map[collector_type]
                            print(f"更新采集器类型映射: {collector_type} -> {primary_entity_type} (之前: {old_entity_type}, 包: {package_name})")
                            self.collector_type_map[collector_type] = primary_entity_type
                            # 更新反向映射
                            if old_entity_type in self.entity_to_collector_type:
                                del self.entity_to_collector_type[old_entity_type]
                            self.entity_to_collector_type[primary_entity_type] = collector_type
                
                # 如果包信息中有实体模型列表或关系模型列表，保存包信息
                if package_info.get("entity_models") or package_info.get("relationship_models"):
                    self.packages[package_name] = package_info
    
    def save_entity_model(self, model: EntityMetaModel, package_name: Optional[str] = None) -> Path:
        """
        保存实体元模型到文件
        
        Args:
            model: 实体元模型
            package_name: 包名（如果为None，保存到根目录）
            
        Returns:
            保存的文件路径
        """
        if package_name:
            # 保存到包文件夹
            package_dir = self.metamodels_dir / package_name
            package_dir.mkdir(parents=True, exist_ok=True)
            file_path = package_dir / f"{model.type}@{model.version}.yaml"
        else:
            # 保存到根目录（向后兼容）
            file_path = self.metamodels_dir / f"{model.type}@{model.version}.yaml"
        
        data = {
            "entity_models": [model.to_dict()],
            "relationship_models": []
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        return file_path
    
    def deploy_package(self, package: MetaModelPackage) -> Dict[str, Any]:
        """
        部署元模型包（热部署）
        
        Args:
            package: 元模型包
            
        Returns:
            部署结果
        """
        results = {
            "success": True,
            "entity_models": [],
            "relationship_models": [],
            "plugins": [],
            "errors": [],
            "package_name": None
        }
        
        # 从包的metadata中获取包名，如果没有则使用默认名称
        package_name = package.metadata.get("name") or package.metadata.get("package_name") or "default"
        if not package_name or package_name == "default":
            # 如果没有指定包名，尝试从第一个实体模型推断
            if package.entity_models:
                # 使用第一个实体模型的类型前缀作为包名
                first_type = package.entity_models[0].type
                package_name = first_type.split("_")[0].lower() if "_" in first_type else first_type.lower()
            else:
                package_name = f"package_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results["package_name"] = package_name
        
        # 创建包文件夹
        package_dir = self.metamodels_dir / package_name
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建包内的插件目录
        package_plugins_dir = package_dir / "plugins"
        package_plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # 部署插件（保存到包文件夹和全局插件目录）
        for plugin_name, plugin_code in package.plugins.items():
            try:
                # 保存到全局插件目录（向后兼容）
                self.plugin_loader.save_plugin(plugin_code, plugin_name)
                # 同时保存到包文件夹
                plugin_file = package_plugins_dir / plugin_name
                with open(plugin_file, 'w', encoding='utf-8') as f:
                    f.write(plugin_code)
                results["plugins"].append({"name": plugin_name, "status": "success"})
            except Exception as e:
                results["errors"].append(f"插件 {plugin_name} 部署失败: {e}")
                results["success"] = False
        
        # 部署实体元模型
        entity_types = []
        for model in package.entity_models:
            try:
                # 注册模型并加载插件（从包文件夹）
                self.register_entity_model(model, reload_plugin=True, package_name=package_name)
                self.save_entity_model(model, package_name=package_name)
                entity_types.append(model.type)
                results["entity_models"].append({"type": model.type, "version": model.version, "status": "success"})
            except Exception as e:
                results["errors"].append(f"实体元模型 {model.type}@{model.version} 部署失败: {e}")
                results["success"] = False
        
        # 注册采集器类型映射
        if package.collector_type and entity_types:
            primary_entity_type = entity_types[0]
            self.collector_type_map[package.collector_type] = primary_entity_type
            self.entity_to_collector_type[primary_entity_type] = package.collector_type
        
        # 部署关系元模型
        relationship_types = []
        for model in package.relationship_models:
            try:
                self.register_relationship_model(model)
                # 保存关系元模型到包文件夹
                file_path = package_dir / f"relationship_{model.type}@{model.version}.yaml"
                data = {
                    "entity_models": [],
                    "relationship_models": [model.to_dict()]
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
                relationship_types.append(model.type)
                results["relationship_models"].append({"type": model.type, "version": model.version, "status": "success"})
            except Exception as e:
                results["errors"].append(f"关系元模型 {model.type}@{model.version} 部署失败: {e}")
                results["success"] = False
        
        # 从包的元模型数据中提取config_schema（如果存在）
        package_config_schema = None
        # 尝试从顶层获取config_schema（新格式）
        if hasattr(package, 'config_schema') and package.config_schema:
            package_config_schema = package.config_schema
        else:
            # 尝试从第一个实体模型的collector中获取config_schema（向后兼容）
            for model in package.entity_models:
                if model.collector and model.collector.get('config_schema'):
                    package_config_schema = model.collector.get('config_schema')
                    break
        
        # 更新包信息
        package_info = {
            "name": package_name,
            "path": str(package_dir),
            "entity_models": entity_types,
            "relationship_models": relationship_types,
            "metadata": package.metadata,
            "collector_type": package.collector_type,
            "deployed_at": datetime.now().isoformat()
        }
        
        # 如果存在config_schema，添加到包信息中
        if package_config_schema:
            package_info["config_schema"] = package_config_schema
        
        self.packages[package_name] = package_info
        
        # 保存包信息文件
        package_info_file = package_dir / "package_info.yaml"
        with open(package_info_file, 'w', encoding='utf-8') as f:
            yaml.dump(package_info, f, allow_unicode=True, default_flow_style=False)
        
        return results
    
    def list_entity_models(self) -> List[Dict[str, Any]]:
        """列出所有实体元模型"""
        return [model.to_dict() for model in self.entity_models.values()]
    
    def list_relationship_models(self) -> List[Dict[str, Any]]:
        """列出所有关系元模型"""
        return [model.to_dict() for model in self.relationship_models.values()]
    
    def list_packages(self) -> List[Dict[str, Any]]:
        """列出所有包"""
        return list(self.packages.values())
    
    def get_package(self, package_name: str) -> Optional[Dict[str, Any]]:
        """获取包信息"""
        return self.packages.get(package_name)
    
    def get_entity_models_by_package(self, package_name: str) -> List[Dict[str, Any]]:
        """根据包名获取实体元模型列表"""
        package = self.packages.get(package_name)
        if not package:
            return []
        
        entity_types = package.get("entity_models", [])
        models = []
        for entity_type in entity_types:
            model = self.get_entity_model(entity_type)
            if model:
                models.append(model.to_dict())
        return models
    
    def get_relationship_models_by_package(self, package_name: str) -> List[Dict[str, Any]]:
        """根据包名获取关系元模型列表"""
        package = self.packages.get(package_name)
        if not package:
            return []
        
        relationship_types = package.get("relationship_models", [])
        models = []
        for relationship_type in relationship_types:
            model = self.get_relationship_model(relationship_type)
            if model:
                models.append(model.to_dict())
        return models
    
    def get_collector_type_by_entity_type(self, entity_type: str) -> Optional[str]:
        """
        根据实体类型获取采集器类型
        
        Args:
            entity_type: 实体类型
            
        Returns:
            采集器类型或None
        """
        return self.entity_to_collector_type.get(entity_type)
    
    def get_entity_type_by_collector_type(self, collector_type: str) -> Optional[str]:
        """
        根据采集器类型获取实体类型
        
        Args:
            collector_type: 采集器类型
            
        Returns:
            实体类型或None
        """
        return self.collector_type_map.get(collector_type)
    
    def list_collector_types(self, package_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有可用的采集器类型
        
        Args:
            package_name: 可选的包名，如果提供则只返回该包内的采集器类型
        
        Returns:
            采集器类型列表，包含类型标识、标签、描述等信息
        """
        collector_types = []
        
        # 如果指定了包名，获取该包内的实体类型列表
        package_entity_types = set()
        if package_name:
            package = self.packages.get(package_name)
            if package:
                package_entity_types = set(package.get("entity_models", []))
        
        for collector_type, entity_type in self.collector_type_map.items():
            # 如果指定了包名，只包含该包内的实体类型
            if package_name and entity_type not in package_entity_types:
                continue
                
            entity_model = self.get_entity_model(entity_type)
            if entity_model:
                collector_types.append({
                    "collector_type": collector_type,
                    "entity_type": entity_type,
                    "label": entity_model.label,
                    "description": entity_model.description,
                    "version": entity_model.version,
                    "enabled": entity_model.enabled
                })
        
        return collector_types
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entity_models": self.list_entity_models(),
            "relationship_models": self.list_relationship_models(),
            "collectors": list(self.collectors.keys()),
            "entity_type_versions": self.entity_type_versions,
            "relationship_type_versions": self.relationship_type_versions,
            "packages": self.list_packages(),
            "collector_types": self.list_collector_types()
        }

