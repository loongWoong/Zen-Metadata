"""
文件系统元数据采集器插件
"""
from src.collectors.base import BaseCollector
from src.core.models import CollectionResult
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import os

class FileSystemCollector(BaseCollector):
    """文件系统元数据采集器"""
    
    def collect(self) -> CollectionResult:
        """采集文件系统元数据"""
        result = CollectionResult()
        
        try:
            scan_paths = self.get_config("scan_paths", [])
            if not scan_paths:
                result.errors.append("缺少必需的配置: scan_paths")
                return result
            
            if isinstance(scan_paths, str):
                scan_paths = [scan_paths]
            
            self.scan_paths = [Path(p) for p in scan_paths]
            self.exclude_patterns = self.get_config("exclude_patterns", [])
            self.max_depth = self.get_config("max_depth", None)
            
            for scan_path in self.scan_paths:
                if not scan_path.exists():
                    result.errors.append(f"路径不存在: {scan_path}")
                    continue
                
                path_result = self._collect_path(scan_path)
                result.entities.extend(path_result.entities)
                result.relationships.extend(path_result.relationships)
                result.errors.extend(path_result.errors)
        
        except Exception as e:
            result.errors.append(f"采集失败: {str(e)}")
        
        return result
    
    def _collect_path(self, path: Path, parent_id: Optional[str] = None, 
                     depth: int = 0) -> CollectionResult:
        """递归采集路径元数据"""
        result = CollectionResult()
        
        # 检查深度限制
        if self.max_depth and depth > self.max_depth:
            return result
        
        # 检查排除模式
        if self._should_exclude(path):
            return result
        
        try:
            if path.is_file():
                # 处理文件
                file_result = self._collect_file(path, parent_id)
                result.entities.extend(file_result.entities)
                result.relationships.extend(file_result.relationships)
            
            elif path.is_dir():
                # 获取实体类型
                entity_type = self.get_entity_type() or "Directory"
                
                # 处理目录
                dir_entity = self.create_entity(
                    entity_type=entity_type,
                    name=path.name,
                    description=f"目录: {path}",
                    properties={
                        "path": str(path),
                        "absolute_path": str(path.absolute()),
                        "depth": depth
                    }
                )
                result.entities.append(dir_entity)
                
                # 创建父子关系
                if parent_id:
                    contains_rel = self.create_relationship(
                        parent_id,
                        dir_entity.id,
                        "CONTAINS"
                    )
                    result.relationships.append(contains_rel)
                
                # 递归处理子项
                try:
                    for item in path.iterdir():
                        item_result = self._collect_path(
                            item, 
                            dir_entity.id, 
                            depth + 1
                        )
                        result.entities.extend(item_result.entities)
                        result.relationships.extend(item_result.relationships)
                        result.errors.extend(item_result.errors)
                except PermissionError:
                    result.errors.append(f"无权限访问: {path}")
        
        except Exception as e:
            result.errors.append(f"处理路径 {path} 失败: {str(e)}")
        
        return result
    
    def _collect_file(self, file_path: Path, parent_id: Optional[str]) -> CollectionResult:
        """采集文件元数据"""
        result = CollectionResult()
        
        try:
            stat = file_path.stat()
            
            file_entity = self.create_entity(
                entity_type="File",
                name=file_path.name,
                description=f"文件: {file_path}",
                properties={
                    "path": str(file_path),
                    "absolute_path": str(file_path.absolute()),
                    "size": stat.st_size,
                    "extension": file_path.suffix,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "is_readonly": not os.access(file_path, os.W_OK)
                }
            )
            result.entities.append(file_entity)
            
            # 创建目录包含文件的关系
            if parent_id:
                contains_rel = self.create_relationship(
                    parent_id,
                    file_entity.id,
                    "CONTAINS"
                )
                result.relationships.append(contains_rel)
        
        except Exception as e:
            result.errors.append(f"采集文件 {file_path} 失败: {str(e)}")
        
        return result
    
    def _should_exclude(self, path: Path) -> bool:
        """检查路径是否应该被排除"""
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str:
                return True
        return False
