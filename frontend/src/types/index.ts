/**
 * 类型定义
 */

export enum MetadataType {
  DATABASE = "database",
  TABLE = "table",
  COLUMN = "column",
  FUNCTION = "function",
  CLASS = "class",
  FILE = "file",
  DIRECTORY = "directory",
  PACKAGE = "package",
  MODULE = "module",
  RELATIONSHIP = "relationship",
  SCHEMA = "schema",
  INDEX = "index",
  CONSTRAINT = "constraint",
}

export enum RelationshipType {
  CONTAINS = "contains",
  DEPENDS_ON = "depends_on",
  REFERENCES = "references",
  IMPLEMENTS = "implements",
  INHERITS = "inherits",
  CALLS = "calls",
  IMPORTS = "imports",
  USES = "uses",
  BELONGS_TO = "belongs_to",
  RELATED_TO = "related_to",
}

export interface MetadataEntity {
  id: string;
  type: MetadataType;
  name: string;
  description?: string;
  properties: Record<string, any>;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface MetadataRelationship {
  id?: number;
  source_id: string;
  target_id: string;
  type: RelationshipType;
  properties: Record<string, any>;
  created_at: string;
}

export interface Task {
  id: string;
  type: string;
  status: TaskStatus;
  progress: number;
  message?: string;
  result?: Record<string, any>;
  error?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export enum TaskStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

export interface Statistics {
  graph?: {
    node_count: number;
    edge_count: number;
  };
  sqlite?: {
    entity_count: number;
    relationship_count: number;
    entity_type_count: number;
    source_count: number;
  };
  duckdb?: {
    entity_count: number;
    relationship_count: number;
  };
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  [key: string]: any;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  [key: string]: any;
}

export interface GraphLayout {
  [nodeId: string]: {
    x: number;
    y: number;
  };
}







