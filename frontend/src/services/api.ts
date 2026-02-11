/**
 * API 服务层
 */
import axios from 'axios';
import type {
  MetadataEntity,
  MetadataRelationship,
  Task,
  Statistics,
  GraphData,
  GraphLayout,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 从localStorage获取token并添加到请求头
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    // 如果是401错误，清除token并跳转到登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      // 可以在这里添加路由跳转到登录页
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const api = {
  // 实体相关
  entities: {
    list: (params?: {
      entity_type?: string;
      source?: string;
      limit?: number;
    }) => apiClient.get<{ entities: MetadataEntity[]; count: number }>('/api/entities', { params }),

    get: (id: string) =>
      apiClient.get<{
        entity: MetadataEntity;
        outgoing_relationships: MetadataRelationship[];
        incoming_relationships: MetadataRelationship[];
      }>(`/api/entities/${id}`),

    getRelationships: (id: string, direction: 'both' | 'outgoing' | 'incoming' = 'both') =>
      apiClient.get<{
        outgoing: MetadataRelationship[];
        incoming: MetadataRelationship[];
      }>(`/api/entities/${id}/relationships`, {
        params: { direction },
      }),

    search: (q: string, params?: { entity_type?: string; source?: string; limit?: number }) =>
      apiClient.get<{
        query: string;
        results: MetadataEntity[];
        count: number;
      }>('/api/search', { params: { q, ...params } }),

    batch: (entityIds: string[]) =>
      apiClient.post<{
        entities: MetadataEntity[];
        count: number;
        requested: number;
      }>('/api/entities/batch', entityIds),
  },

  // 关系相关
  relationships: {
    list: (params?: {
      source_id?: string;
      target_id?: string;
      relationship_type?: string;
      limit?: number;
    }) =>
      apiClient.get<{ relationships: MetadataRelationship[]; count: number }>(
        '/api/relationships',
        { params }
      ),
  },

  // 任务相关
  tasks: {
    create: (data: { collector_type: string; config: Record<string, any> }) =>
      apiClient.post<{ task_id: string; status: string; created_at: string }>(
        '/api/tasks/collect',
        data
      ),

    get: (id: string) =>
      apiClient.get<{
        id: string;
        type: string;
        status: string;
        progress: number;
        message?: string;
        result?: Record<string, any>;
        error?: string;
        config?: Record<string, any>;
        created_at: string;
        started_at?: string;
        completed_at?: string;
      }>(`/api/tasks/${id}`),

    getProgress: (id: string) =>
      apiClient.get<{
        task_id: string;
        status: string;
        progress: number;
        message?: string;
      }>(`/api/tasks/${id}/progress`),

    list: (params?: { status?: string; task_type?: string; limit?: number }) =>
      apiClient.get<{
        tasks: Array<{
          id: string;
          type: string;
          status: string;
          progress: number;
          message?: string;
          created_at: string;
          completed_at?: string;
        }>;
        count: number;
      }>('/api/tasks', { params }),

    update: (id: string, data: { collector_type: string; config: Record<string, any> }) =>
      apiClient.put<{ success: boolean; message: string }>(`/api/tasks/${id}`, data),

    rerun: (id: string) =>
      apiClient.post<{ success: boolean; message: string; task_id: string }>(`/api/tasks/${id}/rerun`),

    delete: (id: string) =>
      apiClient.delete<{ success: boolean; message: string }>(`/api/tasks/${id}`),
  },

  // 查询相关
  query: {
    execute: (query: string, params?: Record<string, any>) =>
      apiClient.post<{
        nodes: any[];
        edges: any[];
        statistics: Record<string, any>;
      }>('/api/query', { query, params }),
  },

  // 可视化相关
  visualize: {
    get: (params?: {
      entity_id?: string;
      entity_type?: string;
      depth?: number;
      layout?: string;
    }) =>
      apiClient.get<{
        graph: GraphData;
        layout: GraphLayout;
        statistics: Record<string, any>;
      }>('/api/visualize', { params }),
  },

  // 统计相关
  statistics: {
    get: () => apiClient.get<Statistics>('/api/statistics'),

    entityDistribution: () =>
      apiClient.get<{ data: Array<{ type: string; count: number; source_count: number }> }>(
        '/api/analytics/entity-distribution'
      ),

    relationshipPatterns: () =>
      apiClient.get<{ data: Array<{ type: string; count: number }> }>(
        '/api/analytics/relationship-patterns'
      ),

    centralEntities: (topN: number = 10) =>
      apiClient.get<{
        data: Array<{
          id: string;
          name: string;
          type: string;
          connection_count: number;
        }>;
      }>('/api/analytics/central-entities', { params: { top_n: topN } }),
  },

  // 导出相关
  export: {
    json: () => apiClient.get('/api/export/json', { responseType: 'blob' }),
    entitiesCsv: () => apiClient.get('/api/export/csv/entities', { responseType: 'blob' }),
    relationshipsCsv: () =>
      apiClient.get('/api/export/csv/relationships', { responseType: 'blob' }),
    graphml: () => apiClient.get('/api/export/graphml', { responseType: 'blob' }),
  },

  // 同步相关
  sync: {
    sync: (incremental: boolean = false) =>
      apiClient.post<{
        success: boolean;
        stats: {
          entities_synced: number;
          relationships_synced: number;
          errors: string[];
        };
      }>('/api/sync', null, { params: { incremental } }),
  },

  // 质量管理相关
  quality: {
    assessEntity: (entityId: string) =>
      apiClient.post<{
        score: {
          entity_id: string;
          entity_type: string;
          completeness_score: number;
          accuracy_score: number;
          consistency_score: number;
          freshness_score: number;
          overall_score: number;
          quality_level: string;
          assessed_at: string;
        };
        alerts: Array<{
          entity_id: string;
          rule_name: string;
          severity: string;
          timestamp: string;
        }>;
      }>('/api/quality/assess/entity', { entity_id: entityId }),

    assessBatch: (data: { entity_ids?: string[]; entity_type?: string; source?: string }) =>
      apiClient.post<{
        scores: Array<any>;
        metrics: {
          total_entities: number;
          assessed_entities: number;
          average_overall: number;
          excellent_count: number;
          good_count: number;
          fair_count: number;
          poor_count: number;
          critical_count: number;
        };
        alerts: Record<string, any[]>;
        count: number;
      }>('/api/quality/assess/batch', data),

    getScores: (params?: { entity_id?: string; entity_type?: string; limit?: number; offset?: number }) =>
      apiClient.get<{
        scores: Array<{
          entity_id: string;
          entity_type: string;
          completeness_score: number;
          accuracy_score: number;
          consistency_score: number;
          freshness_score: number;
          overall_score: number;
          quality_level: string;
          assessed_at: string;
        }>;
        count: number;
        total: number;
        message?: string;
      }>('/api/quality/scores', { params }),

    getMetrics: (params?: { entity_type?: string; source?: string; limit?: number }) =>
      apiClient.get<{
        total_entities: number;
        assessed_entities: number;
        average_completeness: number;
        average_accuracy: number;
        average_consistency: number;
        average_freshness: number;
        average_overall: number;
        excellent_count: number;
        good_count: number;
        fair_count: number;
        poor_count: number;
        critical_count: number;
      }>('/api/quality/metrics', { params }),

    getRules: () =>
      apiClient.get<{
        rules: Array<{
          name: string;
          dimension: string;
          severity: string;
          enabled: boolean;
          description: string;
        }>;
        total_rules: number;
        enabled_rules: number;
      }>('/api/quality/rules'),

    addRule: (data: any) =>
      apiClient.post<{ success: boolean; rule: any }>('/api/quality/rules', data),

    deleteRule: (ruleName: string) =>
      apiClient.delete<{ success: boolean; message: string }>(`/api/quality/rules/${ruleName}`),

    enableRule: (ruleName: string) =>
      apiClient.put<{ success: boolean; message: string }>(`/api/quality/rules/${ruleName}/enable`),

    disableRule: (ruleName: string) =>
      apiClient.put<{ success: boolean; message: string }>(`/api/quality/rules/${ruleName}/disable`),

    getAlerts: (params?: { entity_id?: string; rule_name?: string; severity?: string; limit?: number }) =>
      apiClient.get<{
        alerts: Array<{
          entity_id: string;
          rule_name: string;
          severity: string;
          score: any;
          timestamp: string;
        }>;
        count: number;
      }>('/api/quality/alerts', { params }),

    getAlertStatistics: (days?: number) =>
      apiClient.get<{
        total_alerts: number;
        severity_distribution: Record<string, number>;
        rule_distribution: Record<string, number>;
        period_days: number;
      }>('/api/quality/alerts/statistics', { params: { days } }),
  },

  // 元模型管理相关
  metamodel: {
    listEntityModels: () =>
      apiClient.get<{
        models: Array<{
          type: string;
          version: string;
          label: string;
          description?: string;
          properties: Record<string, any>;
          relationships: Array<any>;
          collector?: any;
          quality_rules?: any;
          enabled: boolean;
        }>;
        count: number;
      }>('/api/metamodel/entities'),

    getEntityModel: (entityType: string, version?: string) =>
      apiClient.get<any>(`/api/metamodel/entities/${entityType}`, {
        params: version ? { version } : {},
      }),

    createEntityModel: (data: any) =>
      apiClient.post<{ success: boolean; model: any; file_path: string }>('/api/metamodel/entities', data),

    deleteEntityModel: (entityType: string, version?: string) =>
      apiClient.delete<{ success: boolean; message: string }>(`/api/metamodel/entities/${entityType}`, {
        params: version ? { version } : {},
      }),

    listRelationshipModels: () =>
      apiClient.get<{
        models: Array<{
          type: string;
          version: string;
          label: string;
          source_types: string[];
          target_types: string[];
          enabled: boolean;
        }>;
        count: number;
      }>('/api/metamodel/relationships'),

    getRelationshipModel: (relationshipType: string, version?: string) =>
      apiClient.get<any>(`/api/metamodel/relationships/${relationshipType}`, {
        params: version ? { version } : {},
      }),

    createRelationshipModel: (data: any) =>
      apiClient.post<{ success: boolean; model: any; file_path: string }>('/api/metamodel/relationships', data),

    listPlugins: () =>
      apiClient.get<{ plugins: string[]; count: number }>('/api/metamodel/plugins'),

    validatePlugin: (code: string) =>
      apiClient.post<{ is_safe: boolean; error?: string }>('/api/metamodel/plugins/validate', { code }),

    deployPackage: (data: {
      entity_models?: any[];
      relationship_models?: any[];
      plugins?: Record<string, string>;
      metadata?: any;
    }) =>
      apiClient.post<{
        success: boolean;
        entity_models: Array<{ type: string; version: string; status: string }>;
        relationship_models: Array<{ type: string; version: string; status: string }>;
        plugins: Array<{ name: string; status: string }>;
        errors: string[];
      }>('/api/metamodel/deploy', data),

    uploadPackage: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post<any>('/api/metamodel/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    getRegistryInfo: () =>
      apiClient.get<{
        entity_models: any[];
        relationship_models: any[];
        collectors: string[];
        entity_type_versions: Record<string, string[]>;
        relationship_type_versions: Record<string, string[]>;
      }>('/api/metamodel/registry'),

    reloadRegistry: () =>
      apiClient.post<{ success: boolean; message: string; registry: any }>('/api/metamodel/registry/reload'),

    // 包管理API
    listPackages: () =>
      apiClient.get<{ packages: any[]; count: number }>('/api/metamodel/packages'),

    getPackage: (packageName: string) =>
      apiClient.get<{
        name: string;
        path: string;
        entity_models: any[];
        relationship_models: any[];
        metadata?: any;
        deployed_at?: string;
      }>(`/api/metamodel/packages/${packageName}`),

    getPackageEntityModels: (packageName: string) =>
      apiClient.get<{ models: any[]; count: number; package_name: string }>(
        `/api/metamodel/packages/${packageName}/entity-models`
      ),

    getPackageRelationshipModels: (packageName: string) =>
      apiClient.get<{ models: any[]; count: number; package_name: string }>(
        `/api/metamodel/packages/${packageName}/relationship-models`
      ),

    listCollectorTypes: (packageName?: string) => {
      const config = packageName ? { params: { package_name: packageName } } : {};
      return apiClient.get<{
        collector_types: Array<{
          collector_type: string;
          entity_type: string;
          label: string;
          description?: string;
          version: string;
          enabled: boolean;
        }>;
        count: number;
      }>('/api/metamodel/collector-types', config);
    },

    updateEntityModelCollector: (entityType: string, version: string | undefined, data: { collector: any }) => {
      const params = version ? { version } : {};
      return apiClient.put<{ success: boolean; message: string; model: any; file_path: string }>(
        `/api/metamodel/entities/${entityType}/collector`,
        data,
        { params }
      );
    },

    getCollectorPluginCode: (collectorType: string) =>
      apiClient.get<{
        code: string;
        plugin_name: string;
        file_path: string;
        package_name?: string;
      }>(`/api/metamodel/collectors/${collectorType}/plugin`),

    updateCollectorPluginCode: (collectorType: string, code: string) =>
      apiClient.put<{
        success: boolean;
        message: string;
        plugin_name: string;
        file_path: string;
        package_name?: string;
      }>(`/api/metamodel/collectors/${collectorType}/plugin`, { code }),
  },

  // 血缘追踪相关
  lineage: {
    discover: (entityId: string, params?: { granularity?: string; max_depth?: number }) =>
      apiClient.get<any>(`/api/lineage/discover/${entityId}`, { params }),

    traceUpstream: (entityId: string, depth?: number) =>
      apiClient.get<any>(`/api/lineage/upstream/${entityId}`, { params: { depth } }),

    traceDownstream: (entityId: string, depth?: number) =>
      apiClient.get<any>(`/api/lineage/downstream/${entityId}`, { params: { depth } }),

    analyzeImpact: (data: { entity_id: string; direction?: string; include_quality?: boolean }) =>
      apiClient.post<any>('/api/lineage/impact', data),

    getImpact: (entityId: string, params?: { direction?: string; include_quality?: boolean }) =>
      apiClient.get<any>(`/api/lineage/impact/${entityId}`, { params }),
  },

  // 搜索相关（增强版）
  search: {
    search: (params: {
      q: string;
      entity_type?: string;
      source?: string;
      limit?: number;
      use_semantic?: boolean;
      use_graph?: boolean;
    }) => apiClient.get<any>('/api/search/', { params }),

    semantic: (params: {
      q: string;
      entity_type?: string;
      source?: string;
      limit?: number;
    }) => apiClient.get<any>('/api/search/semantic', { params }),

    recommend: (entityId: string, limit?: number) =>
      apiClient.get<any>(`/api/search/recommend/${entityId}`, { params: { limit } }),

    searchWithQuality: (params: {
      q: string;
      entity_type?: string;
      source?: string;
      limit?: number;
      min_quality?: number;
    }) => apiClient.get<any>('/api/search/quality', { params }),
  },

  // 版本控制相关
  version: {
    createVersion: (data: {
      entity: any;
      created_by?: string;
      change_reason?: string;
      metamodel_version?: string;
    }) => apiClient.post<any>('/api/version/create', data),

    getVersions: (entityId: string, version?: number) =>
      apiClient.get<any>(`/api/version/${entityId}`, { params: version ? { version } : {} }),

    diffVersions: (entityId: string, version1: number, version2: number) =>
      apiClient.get<any>(`/api/version/${entityId}/diff`, { params: { version1, version2 } }),

    rollback: (data: { entity_id: string; target_version: number }) =>
      apiClient.post<any>('/api/version/rollback', data),

    recordAudit: (data: {
      entity_id: string;
      operation_type: string;
      operator?: string;
      changed_fields?: string[];
      old_value?: any;
      new_value?: any;
      change_reason?: string;
      metadata?: any;
    }) => apiClient.post<any>('/api/version/audit', data),

    getAuditEvents: (params?: {
      entity_id?: string;
      operation_type?: string;
      start_time?: string;
      end_time?: string;
      limit?: number;
    }) => apiClient.get<any>('/api/version/audit/events', { params }),

    getAuditStatistics: (days?: number) =>
      apiClient.get<any>('/api/version/audit/statistics', { params: { days } }),
  },

  // 认证与授权相关
  auth: {
    login: (data: { username: string; password: string }) =>
      apiClient.post<{
        access_token: string;
        token_type: string;
        user: {
          id: string;
          username: string;
          email?: string;
          roles: string[];
          teams: string[];
          spaces: string[];
        };
      }>('/api/auth/login', data),

    register: (data: { username: string; email?: string; password: string }) =>
      apiClient.post<{
        access_token: string;
        token_type: string;
        user: {
          id: string;
          username: string;
          email?: string;
          roles: string[];
        };
      }>('/api/auth/register', data),

    getMe: () =>
      apiClient.get<{
        id: string;
        username: string;
        email?: string;
        roles: string[];
        teams: string[];
        spaces: string[];
        is_active: boolean;
        is_superuser: boolean;
        created_at: string;
        last_login?: string;
      }>('/api/auth/me'),

    createUser: (data: {
      username: string;
      email?: string;
      password?: string;
      roles?: string[];
      is_active?: boolean;
      is_superuser?: boolean;
    }) => apiClient.post<{ success: boolean; user_id: string }>('/api/auth/users', data),

    listUsers: (params?: { limit?: number; offset?: number }) =>
      apiClient.get<{
        users: Array<{
          id: string;
          username: string;
          email?: string;
          roles: string[];
          is_active: boolean;
          created_at: string;
        }>;
        count: number;
      }>('/api/auth/users', { params }),

    createTeam: (data: { name: string; description?: string; members?: string[] }) =>
      apiClient.post<{ success: boolean; team_id: string }>('/api/auth/teams', data),

    listTeams: () =>
      apiClient.get<{
        teams: Array<{
          id: string;
          name: string;
          description?: string;
          members: string[];
          created_at: string;
        }>;
        count: number;
      }>('/api/auth/teams'),

    createSpace: (data: {
      name: string;
      description?: string;
      team_id?: string;
      is_public?: boolean;
      members?: string[];
    }) => apiClient.post<{ success: boolean; space_id: string }>('/api/auth/spaces', data),

    createAPIToken: (data: {
      name: string;
      permissions?: Array<{ resource: string; action: string; scope: string }>;
      expires_days?: number;
    }) =>
      apiClient.post<{
        success: boolean;
        token: string;
        token_id: string;
        expires_at?: string;
      }>('/api/auth/tokens', data),

    listRoles: () =>
      apiClient.get<{
        roles: Array<{
          name: string;
          description?: string;
          permissions: Array<{ resource: string; action: string; scope: string }>;
        }>;
        count: number;
      }>('/api/auth/roles'),

    getRole: (roleName: string) =>
      apiClient.get<{
        name: string;
        description?: string;
        permissions: Array<{ resource: string; action: string; scope: string }>;
      }>(`/api/auth/roles/${roleName}`),

    createRole: (data: {
      name: string;
      description?: string;
      permissions?: Array<{ resource: string; action: string; scope: string }>;
    }) => apiClient.post<{ success: boolean; role_name: string }>('/api/auth/roles', data),

    updateRole: (roleName: string, data: {
      description?: string;
      permissions?: Array<{ resource: string; action: string; scope: string }>;
    }) => apiClient.put<{ success: boolean; role_name: string }>(`/api/auth/roles/${roleName}`, data),

    deleteRole: (roleName: string) =>
      apiClient.delete<{ success: boolean; message: string }>(`/api/auth/roles/${roleName}`),

    updateUser: (userId: string, data: {
      username?: string;
      email?: string;
      password?: string;
      roles?: string[];
      is_active?: boolean;
      is_superuser?: boolean;
    }) => apiClient.put<{ success: boolean; user_id: string }>(`/api/auth/users/${userId}`, data),

    deleteUser: (userId: string) =>
      apiClient.delete<{ success: boolean; message: string }>(`/api/auth/users/${userId}`),

    listAPITokens: () =>
      apiClient.get<{
        tokens: Array<{
          id: string;
          name: string;
          permissions: Array<{ resource: string; action: string; scope: string }>;
          expires_at?: string;
          last_used_at?: string;
          created_at: string;
          is_active: boolean;
        }>;
        count: number;
      }>('/api/auth/tokens'),

    deleteAPIToken: (tokenId: string) =>
      apiClient.delete<{ success: boolean; message: string }>(`/api/auth/tokens/${tokenId}`),
  },

  // 菜单管理相关
  menu: {
    listItems: () =>
      apiClient.get<{
        menus: any[];
        count: number;
      }>('/api/menu/items'),

    listAllItems: () =>
      apiClient.get<{
        menus: any[];
        count: number;
      }>('/api/menu/items/all'),

    createItem: (data: {
      key: string;
      label: string;
      icon?: string;
      path?: string;
      parent_id?: string;
      order?: number;
      required_roles?: string[];
      required_permissions?: Array<{ resource: string; action: string; scope: string }>;
    }) => apiClient.post<{ success: boolean; menu_id: string }>('/api/menu/items', data),

    updateItem: (menuId: string, data: {
      label?: string;
      icon?: string;
      path?: string;
      parent_id?: string;
      order?: number;
      required_roles?: string[];
      required_permissions?: Array<{ resource: string; action: string; scope: string }>;
      is_active?: boolean;
    }) => apiClient.put<{ success: boolean; menu_id: string }>(`/api/menu/items/${menuId}`, data),

    deleteItem: (menuId: string) =>
      apiClient.delete<{ success: boolean; message: string }>(`/api/menu/items/${menuId}`),
  },

  // API管理相关
  apiManagement: {
    listRoutes: () =>
      apiClient.get<{
        routes: Array<{
          id: string;
          path: string;
          method: string;
          summary?: string;
          description?: string;
          required_roles: string[];
          required_permissions: Array<{ resource: string; action: string; scope: string }>;
          is_public: boolean;
        }>;
        count: number;
      }>('/api/api-management/routes'),

    getRoute: (routeId: string) =>
      apiClient.get<{
        id: string;
        path: string;
        method: string;
        summary?: string;
        description?: string;
        required_roles: string[];
        required_permissions: Array<{ resource: string; action: string; scope: string }>;
        is_public: boolean;
        created_at: string;
        updated_at: string;
      }>(`/api/api-management/routes/${routeId}`),

    updateRoute: (routeId: string, data: {
      summary?: string;
      description?: string;
      required_roles?: string[];
      required_permissions?: Array<{ resource: string; action: string; scope: string }>;
      is_public?: boolean;
    }) => apiClient.put<{ success: boolean; route_id: string }>(`/api/api-management/routes/${routeId}`, data),

    getStatistics: () =>
      apiClient.get<{
        total_routes: number;
        public_routes: number;
        protected_routes: number;
        methods: Record<string, number>;
      }>('/api/api-management/statistics'),
  },

  // 协作相关
  collaboration: {
    createComment: (data: {
      entity_id: string;
      content: string;
      parent_id?: string;
      version?: number;
      mentions?: string[];
    }) =>
      apiClient.post<{
        success: boolean;
        comment: {
          id: string;
          entity_id: string;
          user_id: string;
          content: string;
          parent_id?: string;
          version?: number;
          created_at: string;
        };
      }>('/api/collaboration/comments', data),

    getComments: (params: { entity_id: string; version?: number }) =>
      apiClient.get<{
        comments: Array<{
          id: string;
          entity_id: string;
          user_id: string;
          content: string;
          parent_id?: string;
          version?: number;
          mentions: string[];
          created_at: string;
          updated_at: string;
        }>;
        count: number;
      }>('/api/collaboration/comments', { params }),

    updateComment: (commentId: string, data: { content: string }) =>
      apiClient.put<{ success: boolean; comment_id: string }>(
        `/api/collaboration/comments/${commentId}`,
        data
      ),

    deleteComment: (commentId: string) =>
      apiClient.delete<{ success: boolean }>(`/api/collaboration/comments/${commentId}`),

    createAnnotation: (data: {
      entity_id: string;
      tag: string;
      note: string;
      category?: string;
    }) =>
      apiClient.post<{
        success: boolean;
        annotation: {
          id: string;
          entity_id: string;
          user_id: string;
          tag: string;
          note: string;
          category?: string;
          created_at: string;
        };
      }>('/api/collaboration/annotations', data),

    getAnnotations: (params: { entity_id: string }) =>
      apiClient.get<{
        annotations: Array<{
          id: string;
          entity_id: string;
          user_id: string;
          tag: string;
          note: string;
          category?: string;
          created_at: string;
        }>;
        count: number;
      }>('/api/collaboration/annotations', { params }),

    updateAnnotation: (annotationId: string, data: { tag: string; note: string }) =>
      apiClient.put<{ success: boolean; annotation_id: string }>(
        `/api/collaboration/annotations/${annotationId}`,
        data
      ),

    deleteAnnotation: (annotationId: string) =>
      apiClient.delete<{ success: boolean }>(`/api/collaboration/annotations/${annotationId}`),

    createApproval: (data: {
      entity_id: string;
      change_type: string;
      change_data: Record<string, any>;
      level: string;
    }) =>
      apiClient.post<{
        success: boolean;
        approval: {
          id: string;
          entity_id: string;
          change_type: string;
          level: string;
          status: string;
          created_at: string;
        };
      }>('/api/collaboration/approvals', data),

    getApprovals: (params?: { entity_id?: string; status?: string }) =>
      apiClient.get<{
        approvals: Array<{
          id: string;
          entity_id: string;
          change_type: string;
          requester_id: string;
          approver_id?: string;
          level: string;
          status: string;
          comment?: string;
          created_at: string;
          approved_at?: string;
        }>;
        count: number;
      }>('/api/collaboration/approvals', { params }),

    approve: (approvalId: string, comment?: string) =>
      apiClient.post<{ success: boolean; approval_id: string }>(
        `/api/collaboration/approvals/${approvalId}/approve`,
        null,
        { params: comment ? { comment } : {} }
      ),

    reject: (approvalId: string, comment?: string) =>
      apiClient.post<{ success: boolean; approval_id: string }>(
        `/api/collaboration/approvals/${approvalId}/reject`,
        null,
        { params: comment ? { comment } : {} }
      ),

    batchCreateComments: (data: {
      entity_ids: string[];
      content: string;
      parent_id?: string;
      version?: number;
      mentions?: string[];
    }) =>
      apiClient.post<{
        success: boolean;
        total: number;
        succeeded: number;
        failed: number;
        results: Array<{ entity_id: string; success: boolean; comment_id: string }>;
        errors: Array<{ entity_id: string; error: string }>;
      }>('/api/collaboration/comments/batch', data),

    batchCreateAnnotations: (data: {
      entity_ids: string[];
      tag: string;
      note: string;
      category?: string;
    }) =>
      apiClient.post<{
        success: boolean;
        total: number;
        succeeded: number;
        failed: number;
        results: Array<{ entity_id: string; success: boolean; annotation_id: string }>;
        errors: Array<{ entity_id: string; error: string }>;
      }>('/api/collaboration/annotations/batch', data),

    batchCreateApprovals: (data: {
      entity_ids: string[];
      change_type: string;
      change_data: Record<string, any>;
      level: string;
    }) =>
      apiClient.post<{
        success: boolean;
        total: number;
        succeeded: number;
        failed: number;
        results: Array<{ entity_id: string; success: boolean; approval_id: string }>;
        errors: Array<{ entity_id: string; error: string }>;
      }>('/api/collaboration/approvals/batch', data),
  },

  // 数据治理相关
  governance: {
    // 标签管理
    createTag: (data: {
      name: string;
      category: string;
      description?: string;
      color?: string;
      created_by?: string;
    }) =>
      apiClient.post<{ success: boolean; tag: any }>('/api/governance/tags', data),

    listTags: (category?: string) =>
      apiClient.get<{ tags: any[]; count: number }>('/api/governance/tags', {
        params: category ? { category } : {},
      }),

    getTag: (tagId: string) =>
      apiClient.get<{ tag: any }>(`/api/governance/tags/${tagId}`),

    updateTag: (tagId: string, data: {
      name?: string;
      category?: string;
      description?: string;
      color?: string;
    }) =>
      apiClient.put<{ success: boolean; tag: any }>(`/api/governance/tags/${tagId}`, data),

    deleteTag: (tagId: string) =>
      apiClient.delete<{ success: boolean; message: string }>(`/api/governance/tags/${tagId}`),

    addEntityTag: (data: {
      entity_id: string;
      tag_id: string;
      user_id?: string;
      confidence?: number;
      is_auto?: boolean;
    }) =>
      apiClient.post<{ success: boolean; entity_tag: any }>('/api/governance/entity-tags', data),

    batchAddEntityTags: (data: {
      entity_ids: string[];
      tag_id: string;
      user_id?: string;
      confidence?: number;
      is_auto?: boolean;
    }) =>
      apiClient.post<{
        success: boolean;
        total: number;
        succeeded: number;
        failed: number;
        results: Array<{ entity_id: string; success: boolean; entity_tag_id: string }>;
        errors: Array<{ entity_id: string; error: string }>;
      }>('/api/governance/entity-tags/batch', data),

    removeEntityTag: (entityId: string, tagId: string) =>
      apiClient.delete<{ success: boolean; message: string }>('/api/governance/entity-tags', {
        params: { entity_id: entityId, tag_id: tagId },
      }),

    getEntityTags: (entityId: string) =>
      apiClient.get<{ tags: any[]; count: number }>(`/api/governance/entities/${entityId}/tags`),

    batchGetEntityTags: (entityIds: string[]) =>
      apiClient.post<{ tags_map: Record<string, any[]>; count: number }>('/api/governance/entities/tags/batch', entityIds),

    getTaggedEntities: (tagId: string, limit?: number) =>
      apiClient.get<{ entity_ids: string[]; count: number }>(`/api/governance/tags/${tagId}/entities`, {
        params: limit ? { limit } : {},
      }),

    recommendTags: (entityId: string, limit?: number) =>
      apiClient.get<{ recommendations: any[]; count: number }>(
        `/api/governance/entities/${entityId}/tags/recommend`,
        { params: limit ? { limit } : {} }
      ),

    // 数据标准管理
    createStandard: (data: {
      name: string;
      type: string;
      entity_type?: string;
      rule: Record<string, any>;
      description?: string;
      enabled?: boolean;
      created_by?: string;
    }) =>
      apiClient.post<{ success: boolean; standard: any }>('/api/governance/standards', data),

    listStandards: (params?: { type?: string; entity_type?: string }) =>
      apiClient.get<{ standards: any[]; count: number }>('/api/governance/standards', { params }),

    getStandard: (standardId: string) =>
      apiClient.get<{ standard: any }>(`/api/governance/standards/${standardId}`),

    updateStandard: (standardId: string, data: {
      name?: string;
      type?: string;
      entity_type?: string;
      rule?: Record<string, any>;
      description?: string;
      enabled?: boolean;
    }) =>
      apiClient.put<{ success: boolean; standard: any }>(`/api/governance/standards/${standardId}`, data),

    deleteStandard: (standardId: string) =>
      apiClient.delete<{ success: boolean; message: string }>(`/api/governance/standards/${standardId}`),

    validateEntity: (data: { entity_id: string; standard_id?: string }) =>
      apiClient.post<{
        entity_id: string;
        violations: any[];
        count: number;
      }>('/api/governance/standards/validate', data),

    getViolations: (params?: {
      entity_id?: string;
      standard_id?: string;
      status?: string;
    }) =>
      apiClient.get<{ violations: any[]; count: number }>('/api/governance/violations', { params }),

    fixViolation: (violationId: string) =>
      apiClient.put<{ success: boolean; message: string }>(`/api/governance/violations/${violationId}/fix`),

    // 数据目录与发现
    browseCatalog: (params?: {
      category?: string;
      tag_id?: string;
      entity_type?: string;
      source?: string;
      limit?: number;
      offset?: number;
    }) =>
      apiClient.get<{
        entities: any[];
        count: number;
        total: number;
        offset: number;
        limit: number;
      }>('/api/governance/catalog', { params }),

    discoverEntities: (params?: {
      q?: string;
      entity_type?: string;
      limit?: number;
    }) =>
      apiClient.get<{ entities: any[]; count: number }>('/api/governance/discover', { params }),

    getUsageAnalytics: (entityId?: string) =>
      apiClient.get<{
        high_usage: any[];
        low_usage: any[];
        total_entities: number;
      }>('/api/governance/analytics/usage', {
        params: entityId ? { entity_id: entityId } : {},
      }),

    getCategories: () =>
      apiClient.get<{ categories: Array<{ value: string; label: string }> }>('/api/governance/categories'),

    getStandardTypes: () =>
      apiClient.get<{ types: Array<{ value: string; label: string }> }>('/api/governance/standard-types'),
  },

  // 可视化增强相关
  visualization: {
    getCentralityAnalysis: (params?: {
      entity_id?: string;
      entity_type?: string;
      top_n?: number;
    }) =>
      apiClient.get<{
        data: Array<{
          id: string;
          label: string;
          type: string;
          degree: number;
          betweenness: number;
          closeness: number;
        }>;
        total: number;
      }>('/api/visualization/analysis/centrality', { params }),

    getCommunityDetection: (params?: {
      entity_id?: string;
      entity_type?: string;
    }) =>
      apiClient.get<{
        communities: Array<{
          id: number;
          nodes: any[];
          size: number;
        }>;
        count: number;
      }>('/api/visualization/analysis/community', { params }),

    getDashboardMetrics: (role?: string) =>
      apiClient.get<{
        entity_count: number;
        relationship_count: number;
        source_count: number;
        entity_type_count: number;
        quality_score?: number;
        high_risk_count?: number;
      }>('/api/visualization/dashboard/metrics', { params: role ? { role } : {} }),
  },

  // 代理管理相关
  agents: {
    list: () =>
      apiClient.get<{
        agents: Array<{
          id: string;
          name: string;
          type: string;
          status: string;
          host: string;
          port: number;
          last_heartbeat?: string;
          config: any;
        }>;
        count: number;
      }>('/api/visualization/agents'),

    start: (agentId: string) =>
      apiClient.post<{ success: boolean; message: string }>(`/api/visualization/agents/${agentId}/start`),

    stop: (agentId: string) =>
      apiClient.post<{ success: boolean; message: string }>(`/api/visualization/agents/${agentId}/stop`),

    updateConfig: (agentId: string, config: any) =>
      apiClient.put<{ success: boolean; message: string }>(`/api/visualization/agents/${agentId}/config`, config),
  },
};

export default api;



