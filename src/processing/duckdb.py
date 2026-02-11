"""
DuckDB 分析型数据处理
"""
import duckdb
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd

from ..core.models import MetadataEntity, MetadataRelationship


class DuckDBProcessor:
    """DuckDB 数据处理器"""
    
    def __init__(self, database_path: Optional[str] = None):
        """
        初始化 DuckDB 处理器
        
        Args:
            database_path: 数据库文件路径（可选，内存模式如果为None）
        """
        if database_path:
            self.database_path = Path(database_path)
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = duckdb.connect(str(self.database_path))
        else:
            self.conn = duckdb.connect(':memory:')
        
        self._init_schema()
    
    def _init_schema(self):
        """初始化数据库模式"""
        # 创建实体表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id VARCHAR PRIMARY KEY,
                type VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                description VARCHAR,
                source VARCHAR NOT NULL,
                properties VARCHAR,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        # 创建关系表
        # 注意：DuckDB 不支持 SERIAL/BIGSERIAL，使用 BIGINT 作为主键
        # 在插入时，如果不指定 id，DuckDB 不会自动生成，需要手动处理或使用序列
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id BIGINT PRIMARY KEY,
                source_id VARCHAR NOT NULL,
                target_id VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                properties VARCHAR,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            )
        """)
        
        # 创建索引
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)")
    
    def load_from_sqlite(self, sqlite_path: str):
        """
        从 SQLite 加载数据
        
        Args:
            sqlite_path: SQLite 数据库路径
        """
        # DuckDB 可以直接读取 SQLite 数据库
        self.conn.execute(f"""
            CREATE TABLE entities AS 
            SELECT * FROM sqlite_scan('{sqlite_path}', 'entities')
        """)
        
        self.conn.execute(f"""
            CREATE TABLE relationships AS 
            SELECT * FROM sqlite_scan('{sqlite_path}', 'relationships')
        """)
    
    def analyze_entity_distribution(self) -> pd.DataFrame:
        """
        分析实体分布
        
        Returns:
            实体类型分布 DataFrame
        """
        # #region agent log
        import json as json_log
        import time
        log_path = r"g:\data\Zen metadata\.cursor\debug.log"
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"E","location":"duckdb.py:analyze_entity_distribution","message":"Function entry","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        query = """
            SELECT 
                type,
                COUNT(*) as count,
                COUNT(DISTINCT source) as source_count
            FROM entities
            GROUP BY type
            ORDER BY count DESC
        """
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"E","location":"duckdb.py:analyze_entity_distribution","message":"Before query execution","data":{"query":query},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        try:
            result = self.conn.execute(query)
            df = result.df()
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"E","location":"duckdb.py:analyze_entity_distribution","message":"After query execution","data":{"df_shape":df.shape,"df_empty":df.empty,"row_count":len(df)},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            return df
        except Exception as e:
            # #region agent log
            try:
                import traceback
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"E","location":"duckdb.py:analyze_entity_distribution","message":"Query failed","data":{"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()[:500]},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            raise
    
    def analyze_relationship_patterns(self) -> pd.DataFrame:
        """
        分析关系模式
        
        Returns:
            关系类型分布 DataFrame
        """
        query = """
            SELECT 
                type,
                COUNT(*) as count
            FROM relationships
            GROUP BY type
            ORDER BY count DESC
        """
        return self.conn.execute(query).df()
    
    def analyze_source_statistics(self) -> pd.DataFrame:
        """
        分析数据源统计
        
        Returns:
            数据源统计 DataFrame
        """
        query = """
            SELECT 
                source,
                COUNT(*) as entity_count,
                COUNT(DISTINCT type) as type_count
            FROM entities
            GROUP BY source
            ORDER BY entity_count DESC
        """
        return self.conn.execute(query).df()
    
    def find_central_entities(self, top_n: int = 10) -> pd.DataFrame:
        """
        查找中心实体（连接最多的实体）
        
        Args:
            top_n: 返回前N个
            
        Returns:
            中心实体 DataFrame
        """
        query = f"""
            SELECT 
                e.id,
                e.name,
                e.type,
                COUNT(r.id) as connection_count
            FROM entities e
            LEFT JOIN relationships r ON e.id = r.source_id OR e.id = r.target_id
            GROUP BY e.id, e.name, e.type
            ORDER BY connection_count DESC
            LIMIT {top_n}
        """
        return self.conn.execute(query).df()
    
    def analyze_entity_relationships(self, entity_id: str) -> pd.DataFrame:
        """
        分析特定实体的关系
        
        Args:
            entity_id: 实体ID
            
        Returns:
            关系分析 DataFrame
        """
        query = """
            SELECT 
                r.type,
                COUNT(*) as count,
                CASE 
                    WHEN r.source_id = ? THEN 'outgoing'
                    ELSE 'incoming'
                END as direction
            FROM relationships r
            WHERE r.source_id = ? OR r.target_id = ?
            GROUP BY r.type, direction
        """
        return self.conn.execute(query, [entity_id, entity_id, entity_id]).df()
    
    def execute_analytical_query(self, query: str) -> pd.DataFrame:
        """
        执行分析查询
        
        Args:
            query: SQL 查询语句
            
        Returns:
            DataFrame
        """
        return self.conn.execute(query).df()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        entity_count = self.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        relationship_count = self.conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        
        return {
            "entity_count": entity_count,
            "relationship_count": relationship_count
        }
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()



