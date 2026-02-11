"""
元模型管理 API
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import yaml
import json
from pathlib import Path
from datetime import datetime

from ..core.metamodel import (
    EntityMetaModel, RelationshipMetaModel, MetaModelPackage
)
from ..core.metamodel_registry import MetaRegistry
from ..core.plugin_loader import PluginSecurityError


router = APIRouter(prefix="/api/metamodel", tags=["metamodel"])

# 全局注册表实例（在启动时初始化）
meta_registry: Optional[MetaRegistry] = None


def set_dependencies(registry: MetaRegistry):
    """设置依赖"""
    global meta_registry
    meta_registry = registry


# ========== 请求/响应模型 ==========

class CreateEntityModelRequest(BaseModel):
    """创建实体元模型请求"""
    type: str
    version: str = "v1"
    label: str
    description: Optional[str] = None
    properties: Dict[str, Dict[str, Any]] = {}
    relationships: List[Dict[str, Any]] = []
    collector: Optional[Dict[str, Any]] = None
    quality_rules: Optional[Dict[str, Any]] = None
    enabled: bool = True
    created_by: Optional[str] = None


class CreateRelationshipModelRequest(BaseModel):
    """创建关系元模型请求"""
    type: str
    version: str = "v1"
    label: str
    description: Optional[str] = None
    source_types: List[str] = []
    target_types: List[str] = []
    properties: Dict[str, Dict[str, Any]] = {}
    inferable: bool = False
    derivable: bool = False
    enabled: bool = True
    created_by: Optional[str] = None


class DeployPackageRequest(BaseModel):
    """部署元模型包请求"""
    entity_models: List[Dict[str, Any]] = []
    relationship_models: List[Dict[str, Any]] = []
    plugins: Dict[str, str] = {}  # filename -> code
    metadata: Dict[str, Any] = {}
    collector_type: Optional[str] = None
    config_schema: Optional[List[Dict[str, Any]]] = None


# ========== 实体元模型 API ==========

@router.get("/entities", response_model=Dict[str, Any])
async def list_entity_models():
    """列出所有实体元模型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    models = meta_registry.list_entity_models()
    return {
        "models": models,
        "count": len(models)
    }


@router.get("/entities/{entity_type}", response_model=Dict[str, Any])
async def get_entity_model(
    entity_type: str,
    version: Optional[str] = Query(None, description="版本号")
):
    """获取实体元模型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    model = meta_registry.get_entity_model(entity_type, version)
    if not model:
        raise HTTPException(status_code=404, detail=f"实体元模型 {entity_type} 不存在")
    
    return model.to_dict()


@router.post("/entities", response_model=Dict[str, Any])
async def create_entity_model(request: CreateEntityModelRequest):
    """创建实体元模型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    try:
        model = EntityMetaModel(
            type=request.type,
            version=request.version,
            label=request.label,
            description=request.description,
            properties=request.properties,
            relationships=request.relationships,
            collector=request.collector,
            quality_rules=request.quality_rules,
            enabled=request.enabled,
            created_by=request.created_by
        )
        
        success = meta_registry.register_entity_model(model)
        if not success:
            raise HTTPException(status_code=500, detail="注册实体元模型失败")
        
        # 保存到文件
        file_path = meta_registry.save_entity_model(model)
        
        return {
            "success": True,
            "model": model.to_dict(),
            "file_path": str(file_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建实体元模型失败: {str(e)}")


@router.delete("/entities/{entity_type}", response_model=Dict[str, Any])
async def delete_entity_model(
    entity_type: str,
    version: Optional[str] = Query(None, description="版本号")
):
    """删除实体元模型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    model = meta_registry.get_entity_model(entity_type, version)
    if not model:
        raise HTTPException(status_code=404, detail=f"实体元模型 {entity_type} 不存在")
    
    full_type = model.get_full_type()
    if full_type in meta_registry.entity_models:
        del meta_registry.entity_models[full_type]
    
    # 删除文件
    file_path = meta_registry.metamodels_dir / f"{entity_type}@{model.version}.yaml"
    if file_path.exists():
        file_path.unlink()
    
    return {"success": True, "message": f"实体元模型 {full_type} 已删除"}


class UpdateCollectorRequest(BaseModel):
    """更新采集器配置请求"""
    collector: Dict[str, Any]


class UpdatePluginCodeRequest(BaseModel):
    """更新插件代码请求"""
    code: str


@router.put("/entities/{entity_type}/collector", response_model=Dict[str, Any])
async def update_entity_model_collector(
    entity_type: str,
    version: Optional[str] = Query(None, description="版本号"),
    request: UpdateCollectorRequest = Body(...)
):
    """更新实体元模型的采集器配置"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    model = meta_registry.get_entity_model(entity_type, version)
    if not model:
        raise HTTPException(status_code=404, detail=f"实体元模型 {entity_type} 不存在")
    
    try:
        # 更新采集器配置
        model.collector = request.collector
        model.updated_at = datetime.now()
        
        # 重新注册模型以更新采集器
        package_name = None
        # 尝试从包信息中查找
        for pkg_name, pkg_info in meta_registry.packages.items():
            if entity_type in pkg_info.get("entity_models", []):
                package_name = pkg_name
                break
        
        success = meta_registry.register_entity_model(model, reload_plugin=True, package_name=package_name)
        if not success:
            raise HTTPException(status_code=500, detail="更新采集器配置失败")
        
        # 保存到文件
        file_path = meta_registry.save_entity_model(model)
        
        return {
            "success": True,
            "message": "采集器配置已更新",
            "model": model.to_dict(),
            "file_path": str(file_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新采集器配置失败: {str(e)}")


# ========== 关系元模型 API ==========

@router.get("/relationships", response_model=Dict[str, Any])
async def list_relationship_models():
    """列出所有关系元模型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    models = meta_registry.list_relationship_models()
    return {
        "models": models,
        "count": len(models)
    }


@router.get("/relationships/{relationship_type}", response_model=Dict[str, Any])
async def get_relationship_model(
    relationship_type: str,
    version: Optional[str] = Query(None, description="版本号")
):
    """获取关系元模型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    model = meta_registry.get_relationship_model(relationship_type, version)
    if not model:
        raise HTTPException(status_code=404, detail=f"关系元模型 {relationship_type} 不存在")
    
    return model.to_dict()


@router.post("/relationships", response_model=Dict[str, Any])
async def create_relationship_model(request: CreateRelationshipModelRequest):
    """创建关系元模型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    try:
        model = RelationshipMetaModel(
            type=request.type,
            version=request.version,
            label=request.label,
            description=request.description,
            source_types=request.source_types,
            target_types=request.target_types,
            properties=request.properties,
            inferable=request.inferable,
            derivable=request.derivable,
            enabled=request.enabled,
            created_by=request.created_by
        )
        
        success = meta_registry.register_relationship_model(model)
        if not success:
            raise HTTPException(status_code=500, detail="注册关系元模型失败")
        
        # 保存到文件
        file_path = meta_registry.metamodels_dir / f"relationship_{model.type}@{model.version}.yaml"
        data = {
            "entity_models": [],
            "relationship_models": [model.to_dict()]
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        return {
            "success": True,
            "model": model.to_dict(),
            "file_path": str(file_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建关系元模型失败: {str(e)}")


# ========== 采集器类型 API ==========

@router.get("/collector-types", response_model=Dict[str, Any])
async def list_collector_types(package_name: Optional[str] = Query(None, description="包名，如果提供则只返回该包内的采集器类型")):
    """列出所有可用的采集器类型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    collector_types = meta_registry.list_collector_types(package_name=package_name)
    return {
        "collector_types": collector_types,
        "count": len(collector_types)
    }


# ========== 插件管理 API ==========

@router.get("/plugins", response_model=Dict[str, Any])
async def list_plugins():
    """列出所有插件"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    plugins = meta_registry.plugin_loader.list_plugins()
    return {
        "plugins": plugins,
        "count": len(plugins)
    }


@router.post("/plugins/validate", response_model=Dict[str, Any])
async def validate_plugin_code(code: str = Body(..., embed=True)):
    """验证插件代码安全性"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    try:
        is_safe, error = meta_registry.plugin_loader.validate_code(code)
        return {
            "is_safe": is_safe,
            "error": error
        }
    except Exception as e:
        return {
            "is_safe": False,
            "error": str(e)
        }


@router.get("/collectors/{collector_type}/plugin", response_model=Dict[str, Any])
async def get_collector_plugin_code(collector_type: str):
    """获取采集器的插件代码"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    try:
        # 从采集器类型查找实体类型
        entity_type = meta_registry.collector_type_map.get(collector_type)
        if not entity_type:
            raise HTTPException(status_code=404, detail=f"采集器类型 {collector_type} 不存在")
        
        # 获取实体元模型
        model = meta_registry.get_entity_model(entity_type)
        if not model or not model.collector:
            raise HTTPException(status_code=404, detail=f"采集器 {collector_type} 没有配置插件")
        
        plugin_name = model.collector.get("plugin", "").replace(".py", "")
        if not plugin_name:
            raise HTTPException(status_code=404, detail=f"采集器 {collector_type} 没有配置插件文件名")
        
        # 查找插件文件路径
        plugin_file = None
        package_name = None
        
        # 优先从包文件夹查找
        for pkg_name, pkg_info in meta_registry.packages.items():
            if entity_type in pkg_info.get("entity_models", []):
                package_name = pkg_name
                package_dir = meta_registry.metamodels_dir / pkg_name
                package_plugin_file = package_dir / "plugins" / f"{plugin_name}.py"
                if package_plugin_file.exists():
                    plugin_file = package_plugin_file
                    break
        
        # 如果包文件夹中没有，尝试从全局插件目录查找
        if not plugin_file:
            plugin_file = meta_registry.plugin_loader.plugins_dir / f"{plugin_name}.py"
            if not plugin_file.exists():
                raise HTTPException(status_code=404, detail=f"插件文件 {plugin_name}.py 不存在")
        
        # 读取插件代码
        with open(plugin_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        return {
            "code": code,
            "plugin_name": plugin_name,
            "file_path": str(plugin_file),
            "package_name": package_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取插件代码失败: {str(e)}")


@router.put("/collectors/{collector_type}/plugin", response_model=Dict[str, Any])
async def update_collector_plugin_code(
    collector_type: str,
    request: UpdatePluginCodeRequest = Body(...)
):
    """更新采集器的插件代码"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    try:
        code = request.code
        # 验证代码安全性
        is_safe, error = meta_registry.plugin_loader.validate_code(code)
        if not is_safe:
            raise HTTPException(status_code=400, detail=f"插件代码不安全: {error}")
        
        # 从采集器类型查找实体类型
        entity_type = meta_registry.collector_type_map.get(collector_type)
        if not entity_type:
            raise HTTPException(status_code=404, detail=f"采集器类型 {collector_type} 不存在")
        
        # 获取实体元模型
        model = meta_registry.get_entity_model(entity_type)
        if not model or not model.collector:
            raise HTTPException(status_code=404, detail=f"采集器 {collector_type} 没有配置插件")
        
        plugin_name = model.collector.get("plugin", "").replace(".py", "")
        if not plugin_name:
            raise HTTPException(status_code=404, detail=f"采集器 {collector_type} 没有配置插件文件名")
        
        # 查找插件文件路径
        plugin_file = None
        package_name = None
        
        # 优先从包文件夹查找
        for pkg_name, pkg_info in meta_registry.packages.items():
            if entity_type in pkg_info.get("entity_models", []):
                package_name = pkg_name
                package_dir = meta_registry.metamodels_dir / pkg_name
                package_plugin_file = package_dir / "plugins" / f"{plugin_name}.py"
                if package_plugin_file.exists():
                    plugin_file = package_plugin_file
                    break
        
        # 如果包文件夹中没有，使用全局插件目录
        if not plugin_file:
            plugin_file = meta_registry.plugin_loader.plugins_dir / f"{plugin_name}.py"
            # 如果文件不存在，创建它
            plugin_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存插件代码
        with open(plugin_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 重新加载插件
        try:
            collector_class = meta_registry.plugin_loader.load_plugin_from_file(plugin_file)
            meta_registry.collectors[entity_type] = collector_class
            meta_registry.plugin_loader.loaded_plugins[plugin_name] = collector_class
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"重新加载插件失败: {str(e)}")
        
        return {
            "success": True,
            "message": "插件代码已更新并重新加载",
            "plugin_name": plugin_name,
            "file_path": str(plugin_file),
            "package_name": package_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新插件代码失败: {str(e)}")


# ========== 包部署 API ==========

@router.post("/deploy", response_model=Dict[str, Any])
async def deploy_package(request: DeployPackageRequest):
    """部署元模型包（热部署）"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    try:
        # 构建元模型包
        entity_models = [EntityMetaModel(**m) for m in request.entity_models]
        relationship_models = [RelationshipMetaModel(**m) for m in request.relationship_models]
        
        # 从请求中提取config_schema（可能在顶层或metadata中）
        config_schema = request.metadata.get("config_schema") if isinstance(request.metadata, dict) else None
        
        package = MetaModelPackage(
            entity_models=entity_models,
            relationship_models=relationship_models,
            plugins=request.plugins,
            metadata=request.metadata,
            collector_type=request.collector_type or (request.metadata.get("collector_type") if isinstance(request.metadata, dict) else None),
            config_schema=config_schema
        )
        
        # 部署
        results = meta_registry.deploy_package(package)
        
        # 部署成功后，自动重新加载注册表以确保采集器可用
        if results.get("success"):
            try:
                # 重新加载所有元模型（包括新部署的）
                meta_registry.load_all()
            except Exception as reload_err:
                results["errors"] = results.get("errors", [])
                results["errors"].append(f"重新加载注册表失败: {str(reload_err)}")
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"部署失败: {str(e)}")


@router.post("/upload", response_model=Dict[str, Any])
async def upload_package(
    file: UploadFile = File(...)
):
    """上传并部署元模型包文件"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 解析文件
        if file.filename.endswith('.yaml') or file.filename.endswith('.yml'):
            data = yaml.safe_load(content)
        elif file.filename.endswith('.json'):
            data = json.loads(content)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，请使用 YAML 或 JSON")
        
        # 构建元模型包
        entity_models = [EntityMetaModel(**m) for m in data.get('entity_models', [])]
        relationship_models = [RelationshipMetaModel(**m) for m in data.get('relationship_models', [])]
        
        # 从数据中提取config_schema（可能在顶层或metadata中）
        config_schema = data.get('config_schema') or (data.get('metadata', {}).get('config_schema') if isinstance(data.get('metadata'), dict) else None)
        
        package = MetaModelPackage(
            entity_models=entity_models,
            relationship_models=relationship_models,
            plugins=data.get('plugins', {}),
            metadata=data.get('metadata', {}),
            collector_type=data.get('collector_type') or (data.get('metadata', {}).get('collector_type') if isinstance(data.get('metadata'), dict) else None),
            config_schema=config_schema
        )
        
        # 部署
        results = meta_registry.deploy_package(package)
        
        # 部署成功后，自动重新加载注册表以确保采集器可用
        if results.get("success"):
            try:
                # 重新加载所有元模型（包括新部署的）
                meta_registry.load_all()
            except Exception as reload_err:
                results["errors"] = results.get("errors", [])
                results["errors"].append(f"重新加载注册表失败: {str(reload_err)}")
        
        return results
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 解析失败: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


# ========== 注册表信息 API ==========

@router.get("/registry", response_model=Dict[str, Any])
async def get_registry_info():
    """获取注册表信息"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    return meta_registry.to_dict()


@router.post("/registry/reload", response_model=Dict[str, Any])
async def reload_registry():
    """重新加载所有元模型（热部署）"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    try:
        # 清空注册表
        meta_registry.entity_models.clear()
        meta_registry.relationship_models.clear()
        meta_registry.collectors.clear()
        meta_registry.entity_type_versions.clear()
        meta_registry.relationship_type_versions.clear()
        meta_registry.packages.clear()
        
        # 重新加载
        meta_registry.load_all()
        
        return {
            "success": True,
            "message": "注册表已重新加载",
            "registry": meta_registry.to_dict()
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=f"重新加载失败: {error_detail}")


# ========== 包管理 API ==========

@router.get("/packages", response_model=Dict[str, Any])
async def list_packages():
    """列出所有包"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    packages = meta_registry.list_packages()
    return {
        "packages": packages,
        "count": len(packages)
    }


@router.get("/packages/{package_name}", response_model=Dict[str, Any])
async def get_package(package_name: str):
    """获取包信息"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    package = meta_registry.get_package(package_name)
    if not package:
        raise HTTPException(status_code=404, detail=f"包 {package_name} 不存在")
    
    # 获取包内的实体和关系元模型
    entity_models = meta_registry.get_entity_models_by_package(package_name)
    relationship_models = meta_registry.get_relationship_models_by_package(package_name)
    
    return {
        **package,
        "entity_models": entity_models,
        "relationship_models": relationship_models
    }


@router.get("/packages/{package_name}/entity-models", response_model=Dict[str, Any])
async def get_package_entity_models(package_name: str):
    """获取包内的实体元模型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    models = meta_registry.get_entity_models_by_package(package_name)
    return {
        "models": models,
        "count": len(models),
        "package_name": package_name
    }


@router.get("/packages/{package_name}/relationship-models", response_model=Dict[str, Any])
async def get_package_relationship_models(package_name: str):
    """获取包内的关系元模型"""
    if not meta_registry:
        raise HTTPException(status_code=500, detail="元模型注册表未初始化")
    
    models = meta_registry.get_relationship_models_by_package(package_name)
    return {
        "models": models,
        "count": len(models),
        "package_name": package_name
    }

