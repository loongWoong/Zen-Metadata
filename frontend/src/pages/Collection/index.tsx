import { useEffect, useState } from 'react';
import {
  Card,
  Form,
  Select,
  Input,
  Button,
  Table,
  Space,
  Tag,
  Progress,
  Modal,
  InputNumber,
  message,
  Checkbox,
} from 'antd';
import { PlayCircleOutlined, ReloadOutlined, DeleteOutlined, RedoOutlined, EditOutlined, HistoryOutlined, CaretRightOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import type { Task } from '../../types';
import { TaskStatus } from '../../types';

const { Option } = Select;
const { TextArea } = Input;

type CollectorType = 'relational' | 'graphdb' | 'code' | 'filesystem' | string;

interface CollectorOption {
  value: string;
  label: string;
  isDefault: boolean;
  isMetamodel: boolean;
  configSchema?: any[]; // 配置schema，用于动态生成表单
  entityType?: string; // 实体类型，用于查找schema
  packageName?: string; // 包名
}

interface PackageOption {
  value: string;
  label: string;
  entityModels: any[];
}

export default function Collection() {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [pollingTasks, setPollingTasks] = useState<Set<string>>(new Set());
  const [collectorType, setCollectorType] = useState<CollectorType>('');
  const [editCollectorType, setEditCollectorType] = useState<CollectorType>('');
  const [showHistory, setShowHistory] = useState(false);
  const [editedTasks, setEditedTasks] = useState<Set<string>>(new Set()); // 跟踪被编辑过的任务
  const [collectorOptions, setCollectorOptions] = useState<CollectorOption[]>([]);
  const [packageOptions, setPackageOptions] = useState<PackageOption[]>([]);
  const [selectedPackage, setSelectedPackage] = useState<string>('');

  const loadTasks = async () => {
    try {
      setLoading(true);
      const response = await api.tasks.list({ limit: 50 });
      setTasks(response.data.tasks);
    } catch (err) {
      console.error('加载任务失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
    loadPackages();
    loadCollectorOptions();
    const interval = setInterval(loadTasks, 5000); // 每5秒刷新一次
    
    // 监听元模型更新事件（当元模型管理页面部署新模型时）
    const handleMetamodelUpdate = () => {
      loadPackages(); // 重新加载包列表
      loadCollectorOptions(selectedPackage || undefined); // 重新加载采集器选项
    };
    
    // 监听自定义事件
    window.addEventListener('metamodel-updated', handleMetamodelUpdate);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('metamodel-updated', handleMetamodelUpdate);
    };
  }, [selectedPackage]);

  const loadPackages = async () => {
    try {
      const response = await api.metamodel.listPackages();
      const packages: PackageOption[] = [];
      
      if (response.data?.packages) {
        response.data.packages.forEach((pkg: any) => {
          packages.push({
            value: pkg.name,
            label: `${pkg.name} (${pkg.entity_models?.length || 0} 个实体模型)`,
            entityModels: pkg.entity_models || [],
          });
        });
      }
      
      setPackageOptions(packages);
    } catch (err) {
      console.error('加载包列表失败:', err);
      setPackageOptions([]);
    }
  };

  const loadCollectorOptions = async (packageName?: string) => {
    try {
      // 如果没有选择包，只显示系统内置的采集器类型
      if (!packageName) {
        const defaultCollectors: CollectorOption[] = [
          { value: 'relational', label: '关系型数据库', isDefault: true, isMetamodel: false },
          { value: 'graphdb', label: '图数据库', isDefault: true, isMetamodel: false },
          { value: 'code', label: '代码元数据', isDefault: true, isMetamodel: false },
          { value: 'filesystem', label: '文件系统', isDefault: true, isMetamodel: false },
        ];
        setCollectorOptions(defaultCollectors);
        return;
      }

      // 如果选择了包，只显示该包内的采集器类型
      const metamodelCollectors: CollectorOption[] = [];

      // 从API获取该包内定义的采集器类型
      try {
        const collectorTypesResponse = await api.metamodel.listCollectorTypes(packageName);
        
        if (collectorTypesResponse.data?.collector_types) {
          // 首先获取包信息，优先从包信息中获取config_schema（新格式）
          let packageConfigSchema: any[] | null = null;
          try {
            const packageResponse = await api.metamodel.getPackage(packageName);
            if (packageResponse.data?.config_schema) {
              packageConfigSchema = packageResponse.data.config_schema;
            }
          } catch (packageErr) {
            console.warn(`获取包信息失败:`, packageErr);
          }
          
          // 批量获取实体模型详情
          const entityTypePromises = collectorTypesResponse.data.collector_types
            .filter((ct: any) => ct.enabled !== false)
            .map(async (ct: any) => {
              let configSchema: any[] = [];
              
              // 优先使用包信息中的config_schema（新格式）
              if (packageConfigSchema) {
                configSchema = packageConfigSchema;
              } else {
                // 如果包信息中没有，尝试从实体模型中获取
                try {
                  const entityResponse = await api.metamodel.getEntityModel(ct.entity_type);
                  const entityModel = entityResponse.data;
                  // 向后兼容：从实体模型的collector中获取（旧格式）
                  if (entityModel?.collector?.config_schema) {
                    configSchema = entityModel.collector.config_schema;
                  }
                } catch (err) {
                  console.error(`获取实体模型 ${ct.entity_type} 失败:`, err);
                  // 如果获取实体模型失败，尝试从包信息中的实体模型列表获取（向后兼容）
                  try {
                    const packageResponse = await api.metamodel.getPackage(packageName);
                    const entityModel = packageResponse.data?.entity_models?.find((m: any) => m.type === ct.entity_type);
                    if (entityModel?.collector?.config_schema) {
                      configSchema = entityModel.collector.config_schema;
                    }
                  } catch (packageErr) {
                    console.error(`从包信息获取实体模型失败:`, packageErr);
                  }
                }
              }
              
              return {
                value: ct.collector_type,
                label: ct.label || ct.collector_type,
                isDefault: false,
                isMetamodel: true,
                configSchema: configSchema,
                entityType: ct.entity_type,
                packageName: packageName,
              };
            });
          
          const collectors = await Promise.all(entityTypePromises);
          metamodelCollectors.push(...collectors);
        }
      } catch (err) {
        console.error('从API加载采集器类型失败:', err);
        // 如果API失败，尝试从包信息中获取实体模型
        try {
          const packageResponse = await api.metamodel.getPackage(packageName);
          if (packageResponse.data?.entity_models) {
            packageResponse.data.entity_models.forEach((model: any) => {
              if (model.collector && model.collector.plugin) {
                // 尝试从collector_type获取，如果没有则从plugin名称推断
                const collectorType = model.collector_type || 
                  model.collector.plugin.replace('.py', '').replace('_collector', '');
                
                metamodelCollectors.push({
                  value: collectorType,
                  label: model.label || model.type,
                  isDefault: false,
                  isMetamodel: true,
                  configSchema: model.collector?.config_schema || [],
                  entityType: model.type,
                  packageName: packageName,
                });
              }
            });
          }
        } catch (fallbackErr) {
          console.error('回退方法加载元模型采集器失败:', fallbackErr);
        }
      }

      // 只显示该包内的采集器类型
      setCollectorOptions(metamodelCollectors);
    } catch (err: any) {
      console.error('加载采集器选项失败:', err);
      // 错误处理：如果没有选择包，显示系统内置的；如果选择了包但没有找到采集器，显示空列表
      if (!packageName) {
        setCollectorOptions([
          { value: 'relational', label: '关系型数据库', isDefault: true, isMetamodel: false },
          { value: 'graphdb', label: '图数据库', isDefault: true, isMetamodel: false },
          { value: 'code', label: '代码元数据', isDefault: true, isMetamodel: false },
          { value: 'filesystem', label: '文件系统', isDefault: true, isMetamodel: false },
        ]);
      } else {
        setCollectorOptions([]);
      }
    }
  };

  // 轮询运行中的任务
  useEffect(() => {
    const interval = setInterval(async () => {
      for (const taskId of pollingTasks) {
        // 跳过临时任务ID（以temp_开头）
        if (taskId.startsWith('temp_')) {
          continue;
        }
        try {
          const response = await api.tasks.getProgress(taskId);
          const task = tasks.find((t) => t.id === taskId);
          if (task) {
            if (response.data.status !== TaskStatus.RUNNING) {
              setPollingTasks((prev) => {
                const next = new Set(prev);
                next.delete(taskId);
                return next;
              });
            }
            loadTasks(); // 刷新整个列表
          }
        } catch (err) {
          console.error('获取任务进度失败:', err);
          // 如果任务不存在（可能已被删除），从轮询列表中移除
          if ((err as any)?.response?.status === 404) {
            setPollingTasks((prev) => {
              const next = new Set(prev);
              next.delete(taskId);
              return next;
            });
          }
        }
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [pollingTasks, tasks]);

  // 根据config_schema动态生成表单字段
  const renderConfigFields = (schema: any[], formInstance: any) => {
    if (!schema || schema.length === 0) return null;
    
    return schema.map((field: any) => {
      const { name, type, label, description, required, default: defaultValue, placeholder, min, max, values } = field;
      
      const rules = required ? [{ required: true, message: `请输入${label}` }] : [];
      
      let fieldComponent;
      switch (type) {
        case 'string':
          fieldComponent = (
            <Form.Item
              key={name}
              name={name}
              label={label}
              tooltip={description}
              rules={rules}
              initialValue={defaultValue}
            >
              <Input placeholder={placeholder || label} />
            </Form.Item>
          );
          break;
        case 'integer':
        case 'number':
          fieldComponent = (
            <Form.Item
              key={name}
              name={name}
              label={label}
              tooltip={description}
              rules={rules}
              initialValue={defaultValue}
            >
              <InputNumber 
                placeholder={placeholder || label} 
                style={{ width: '100%' }} 
                min={min}
                max={max}
              />
            </Form.Item>
          );
          break;
        case 'boolean':
          fieldComponent = (
            <Form.Item
              key={name}
              name={name}
              label={label}
              tooltip={description}
              rules={rules}
              valuePropName="checked"
              initialValue={defaultValue !== undefined ? defaultValue : false}
            >
              <Checkbox>{label}</Checkbox>
            </Form.Item>
          );
          break;
        case 'enum':
          fieldComponent = (
            <Form.Item
              key={name}
              name={name}
              label={label}
              tooltip={description}
              rules={rules}
              initialValue={defaultValue}
            >
              <Select placeholder={placeholder || `请选择${label}`}>
                {values?.map((val: any) => (
                  <Option key={val} value={val}>{val}</Option>
                ))}
              </Select>
            </Form.Item>
          );
          break;
        case 'textarea':
          fieldComponent = (
            <Form.Item
              key={name}
              name={name}
              label={label}
              tooltip={description}
              rules={rules}
              initialValue={defaultValue}
            >
              <TextArea 
                rows={3} 
                placeholder={placeholder || label}
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>
          );
          break;
        case 'json':
          // JSON类型字段：如果有options字段，使用多选框+自定义输入的方式
          if (field.options && Array.isArray(field.options)) {
            // 使用多选框+自定义输入的方式
            fieldComponent = (
              <Form.Item
                key={name}
                label={label}
                tooltip={description}
                required={required}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Form.Item
                    name={[name, 'selected']}
                    label="选择选项"
                    initialValue={defaultValue && Array.isArray(defaultValue) ? defaultValue.filter((v: any) => field.options.includes(v)) : []}
                  >
                    <Checkbox.Group>
                      {field.options.map((option: any) => (
                        <Checkbox key={option} value={option}>{option}</Checkbox>
                      ))}
                    </Checkbox.Group>
                  </Form.Item>
                  <Form.Item
                    name={[name, 'custom']}
                    label="自定义值（JSON数组格式）"
                    tooltip='可以输入额外的值，格式如：["custom1", "custom2"]'
                  >
                    <TextArea 
                      rows={2} 
                      placeholder='["custom1", "custom2"]'
                      style={{ fontFamily: 'monospace' }}
                    />
                  </Form.Item>
                </Space>
              </Form.Item>
            );
          } else {
            // 没有options，使用TextArea，支持输入JSON格式
            fieldComponent = (
              <Form.Item
                key={name}
                name={name}
                label={label}
                tooltip={description}
                rules={rules}
                initialValue={defaultValue !== undefined ? (typeof defaultValue === 'string' ? defaultValue : JSON.stringify(defaultValue)) : undefined}
              >
                <TextArea 
                  rows={3} 
                  placeholder={placeholder || label}
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
            );
          }
          break;
        default:
          fieldComponent = (
            <Form.Item
              key={name}
              name={name}
              label={label}
              tooltip={description}
              rules={rules}
              initialValue={defaultValue}
            >
              <Input placeholder={placeholder || label} />
            </Form.Item>
          );
      }
      
      return fieldComponent;
    });
  };

  const buildConfig = (values: any, type: CollectorType): Record<string, any> => {
    const config: Record<string, any> = {};
    
    // 检查是否是元模型定义的采集器
    const collectorOption = collectorOptions.find(opt => opt.value === type);
    if (collectorOption && collectorOption.isMetamodel) {
      // 对于元模型采集器，处理配置
      // 元模型采集器的配置格式可能不同，这里使用通用方式
      Object.keys(values).forEach(key => {
        if (key !== 'collector_type' && key !== 'package_name') {
          // 处理多选+自定义输入的字段（格式为 { selected: [...], custom: "..." }）
          if (values[key] && typeof values[key] === 'object' && !Array.isArray(values[key]) && values[key].selected !== undefined) {
            // 合并选中的值和自定义值
            const selected = Array.isArray(values[key].selected) ? values[key].selected : [];
            let custom = [];
            if (values[key].custom) {
              try {
                const customParsed = typeof values[key].custom === 'string' 
                  ? JSON.parse(values[key].custom) 
                  : values[key].custom;
                custom = Array.isArray(customParsed) ? customParsed : [];
              } catch (e) {
                // 如果解析失败，忽略自定义值
                console.warn(`解析自定义值失败: ${values[key].custom}`, e);
              }
            }
            // 合并并去重
            config[key] = [...new Set([...selected, ...custom])];
          } else {
            config[key] = values[key];
          }
        }
      });
      // 如果指定了包名，添加到配置中
      if (values.package_name) {
        config.package_name = values.package_name;
      }
      config.source = values.source || 'metamodel';
      return config;
    }
    
    switch (type) {
      case 'relational':
        config.type = values.db_type || 'postgresql';
        config.host = values.host;
        config.port = values.port;
        config.database = values.database;
        config.username = values.username;
        config.password = values.password;
        if (values.source) {
          config.source = values.source;
        }
        break;
        
      case 'graphdb':
        config.db_type = values.graphdb_type || 'neo4j';
        if (config.db_type === 'neo4j') {
          config.connection_config = {
            uri: values.uri,
            username: values.username,
            password: values.password,
          };
        } else if (config.db_type === 'falkordb') {
          config.connection_config = {
            host: values.host,
            port: values.port,
            password: values.password || '',
            graph_name: values.graph_name,
          };
        }
        if (values.source) {
          config.source = values.source;
        }
        break;
        
      case 'code':
        config.source_path = values.source_path;
        config.languages = values.languages || ['python'];
        if (values.source) {
          config.source = values.source;
        }
        // 处理排除模式：将文本按行分割成数组
        if (values.exclude_patterns) {
          const patterns = typeof values.exclude_patterns === 'string'
            ? values.exclude_patterns.split('\n').filter(p => p.trim())
            : (Array.isArray(values.exclude_patterns) ? values.exclude_patterns : []);
          if (patterns.length > 0) {
            config.exclude_patterns = patterns;
          }
        }
        break;
        
      case 'filesystem':
        // 处理扫描路径：将文本按行分割成数组
        if (values.scan_paths) {
          config.scan_paths = typeof values.scan_paths === 'string'
            ? values.scan_paths.split('\n').filter(p => p.trim())
            : (Array.isArray(values.scan_paths) ? values.scan_paths : []);
        } else {
          config.scan_paths = [];
        }
        if (values.source) {
          config.source = values.source;
        }
        // 处理排除模式：将文本按行分割成数组
        if (values.exclude_patterns) {
          const patterns = typeof values.exclude_patterns === 'string'
            ? values.exclude_patterns.split('\n').filter(p => p.trim())
            : (Array.isArray(values.exclude_patterns) ? values.exclude_patterns : []);
          if (patterns.length > 0) {
            config.exclude_patterns = patterns;
          }
        }
        if (values.max_depth) {
          config.max_depth = values.max_depth;
        }
        break;
    }
    
    return config;
  };

  const handleCreateTask = async (values: any) => {
    // 立即关闭弹窗并重置表单
    setCreateModalVisible(false);
    form.resetFields();
    setCollectorType('');
    setSelectedPackage('');
    
    // 构建配置
    const config = buildConfig(values, values.collector_type);
    
    // 创建临时任务（乐观更新）
    const tempTaskId = `temp_${Date.now()}`;
    const tempTask: Task = {
      id: tempTaskId,
      type: `collect_${values.collector_type}`,
      status: TaskStatus.PENDING,
      progress: 0,
      message: '正在创建任务...',
      created_at: new Date().toISOString(),
    };
    
    // 立即添加到任务列表
    setTasks((prev) => [tempTask, ...prev]);
    setPollingTasks((prev) => new Set([...prev, tempTaskId]));
    
    // 异步创建任务
    try {
      const response = await api.tasks.create({
        collector_type: values.collector_type,
        config,
      });
      
      const realTaskId = response.data.task_id;
      
      // 更新任务ID（从临时ID替换为真实ID）
      setTasks((prev) =>
        prev.map((task) =>
          task.id === tempTaskId
            ? {
                ...task,
                id: realTaskId,
                message: '任务已创建，等待执行...',
              }
            : task
        )
      );
      
      // 更新轮询任务集合（先移除临时ID，添加真实ID）
      setPollingTasks((prev) => {
        const next = new Set(prev);
        next.delete(tempTaskId);
        next.add(realTaskId);
        return next;
      });
      
      // 立即刷新任务列表以获取最新状态（包含真实任务信息）
      loadTasks();
    } catch (err: any) {
      // 创建失败，移除临时任务
      setTasks((prev) => prev.filter((task) => task.id !== tempTaskId));
      setPollingTasks((prev) => {
        const next = new Set(prev);
        next.delete(tempTaskId);
        return next;
      });
      message.error(err.message || '创建任务失败');
    }
  };

  const handleCollectorTypeChange = (value: CollectorType) => {
    setCollectorType(value);
    // 重置表单字段，但保留采集器类型
    const currentValues = form.getFieldsValue();
    form.setFieldsValue({ collector_type: value });
    form.resetFields(['db_type', 'host', 'port', 'database', 'username', 'password', 
      'graphdb_type', 'uri', 'graph_name', 'source_path', 'languages', 
      'scan_paths', 'source', 'exclude_patterns', 'max_depth']);
  };

  const handleEditCollectorTypeChange = (value: CollectorType) => {
    setEditCollectorType(value);
    // 重置表单字段，但保留采集器类型
    editForm.setFieldsValue({ collector_type: value });
    editForm.resetFields(['db_type', 'host', 'port', 'database', 'username', 'password', 
      'graphdb_type', 'uri', 'graph_name', 'source_path', 'languages', 
      'scan_paths', 'source', 'exclude_patterns', 'max_depth']);
  };

  const getStatusTag = (status: string) => {
    const colorMap: Record<string, string> = {
      [TaskStatus.PENDING]: 'default',
      [TaskStatus.RUNNING]: 'processing',
      [TaskStatus.COMPLETED]: 'success',
      [TaskStatus.FAILED]: 'error',
      [TaskStatus.CANCELLED]: 'warning',
    };
    return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
  };

  // 从任务类型推断采集器类型
  const getCollectorTypeFromTaskType = (taskType: string, taskConfig?: any): CollectorType => {
    const typeMap: Record<string, CollectorType> = {
      'collect_relational': 'relational',
      'collect_graphdb': 'graphdb',
      'collect_code': 'code',
      'collect_filesystem': 'filesystem',
      'collect_metamodel': taskConfig?.collector_type || '', // 元模型采集器从配置中获取
    };
    return typeMap[taskType] || (taskConfig?.collector_type as CollectorType) || '';
  };

  // 将配置转换为表单值
  const configToFormValues = (config: Record<string, any>, collectorType: CollectorType): Record<string, any> => {
    const values: Record<string, any> = { collector_type: collectorType };
    
    // 检查是否是元模型定义的采集器
    const collectorOption = collectorOptions.find(opt => opt.value === collectorType);
    if (collectorOption && collectorOption.isMetamodel) {
      // 对于元模型采集器，处理配置
      // 需要检查是否有使用多选+自定义输入的字段
      Object.keys(config).forEach(key => {
        // 检查这个字段是否在config_schema中定义了options
        const fieldSchema = collectorOption.configSchema?.find((f: any) => f.name === key);
        if (fieldSchema && fieldSchema.type === 'json' && fieldSchema.options && Array.isArray(fieldSchema.options)) {
          // 这是一个多选+自定义输入的字段
          const configValue = config[key];
          if (Array.isArray(configValue)) {
            // 将数组值分为选中的（在options中的）和自定义的（不在options中的）
            const selected = configValue.filter((v: any) => fieldSchema.options.includes(v));
            const custom = configValue.filter((v: any) => !fieldSchema.options.includes(v));
            values[key] = {
              selected: selected,
              custom: custom.length > 0 ? JSON.stringify(custom) : ''
            };
          } else {
            // 如果不是数组，保持原值
            values[key] = configValue;
          }
        } else {
          values[key] = config[key];
        }
      });
      return values;
    }
    
    switch (collectorType) {
      case 'relational':
        values.db_type = config.type || 'postgresql';
        values.host = config.host || '';
        values.port = config.port || '';
        values.database = config.database || '';
        values.username = config.username || '';
        values.password = config.password || '';
        values.source = config.source || '';
        break;
        
      case 'graphdb':
        values.graphdb_type = config.db_type || 'neo4j';
        if (values.graphdb_type === 'neo4j') {
          values.uri = config.connection_config?.uri || '';
          values.username = config.connection_config?.username || '';
          values.password = config.connection_config?.password || '';
        } else if (values.graphdb_type === 'falkordb') {
          values.host = config.connection_config?.host || '';
          values.port = config.connection_config?.port || '';
          values.password = config.connection_config?.password || '';
          values.graph_name = config.connection_config?.graph_name || '';
        }
        values.source = config.source || '';
        break;
        
      case 'code':
        values.source_path = config.source_path || '';
        values.languages = config.languages || ['python'];
        values.source = config.source || '';
        values.exclude_patterns = Array.isArray(config.exclude_patterns) 
          ? config.exclude_patterns.join('\n')
          : (config.exclude_patterns || '');
        break;
        
      case 'filesystem':
        values.scan_paths = Array.isArray(config.scan_paths)
          ? config.scan_paths.join('\n')
          : (config.scan_paths || '');
        values.source = config.source || '';
        values.exclude_patterns = Array.isArray(config.exclude_patterns)
          ? config.exclude_patterns.join('\n')
          : (config.exclude_patterns || '');
        values.max_depth = config.max_depth || undefined;
        break;
    }
    
    return values;
  };

  // 编辑任务
  const handleEditTask = async (task: Task) => {
    try {
      // 获取任务详情
      const taskDetail = await api.tasks.get(task.id);
      const collectorType = getCollectorTypeFromTaskType(taskDetail.data.type, taskDetail.data.config);
      
      if (!collectorType || !taskDetail.data.config) {
        message.error('无法获取任务配置');
        return;
      }
      
      setEditingTask(task);
      setEditCollectorType(collectorType);
      const formValues = configToFormValues(taskDetail.data.config, collectorType);
      editForm.setFieldsValue(formValues);
      setEditModalVisible(true);
    } catch (err: any) {
      message.error(err.message || '获取任务详情失败');
    }
  };

  // 保存编辑
  const handleUpdateTask = async (values: any) => {
    if (!editingTask) return;
    
    try {
      const config = buildConfig(values, values.collector_type);
      await api.tasks.update(editingTask.id, {
        collector_type: values.collector_type,
        config,
      });
      message.success('任务已更新');
      // 标记任务为已编辑
      setEditedTasks((prev) => new Set([...prev, editingTask.id]));
      setEditModalVisible(false);
      editForm.resetFields();
      setEditingTask(null);
      setEditCollectorType('');
      loadTasks();
    } catch (err: any) {
      message.error(err.message || '更新任务失败');
    }
  };

  // 删除任务
  const handleDeleteTask = async (taskId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个任务吗？',
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.tasks.delete(taskId);
          message.success('任务已删除');
          loadTasks();
        } catch (err: any) {
          message.error(err.message || '删除任务失败');
        }
      },
    });
  };

  // 启动任务（编辑后创建新任务）
  const handleStartTask = async (task: Task) => {
    Modal.confirm({
      title: '确认启动任务',
      content: '将基于当前配置创建新任务并开始运行',
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          // 获取任务详情以获取完整配置
          const taskDetail = await api.tasks.get(task.id);
          const collectorType = getCollectorTypeFromTaskType(taskDetail.data.type, taskDetail.data.config);
          
          if (!collectorType) {
            message.error('无法识别任务类型，无法启动');
            return;
          }

          if (!taskDetail.data.config) {
            message.error('任务配置不存在，无法启动');
            return;
          }

          // 使用当前任务的配置创建新任务
          const response = await api.tasks.create({
            collector_type: collectorType,
            config: taskDetail.data.config,
          });
          
          message.success('新任务已创建并开始运行');
          // 清除编辑标记（因为已经创建了新任务）
          setEditedTasks((prev) => {
            const next = new Set(prev);
            next.delete(task.id);
            return next;
          });
          loadTasks();
          setPollingTasks((prev) => new Set([...prev, response.data.task_id]));
        } catch (err: any) {
          message.error(err.message || '启动任务失败');
        }
      },
    });
  };

  // 重跑任务（增量采集模式）
  const handleRerunTask = async (task: Task) => {
    Modal.confirm({
      title: '确认重新运行',
      content: '将重新运行当前任务，已采集的数据将进行增量更新',
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.tasks.rerun(task.id);
          message.success('任务已开始重新运行（增量采集模式）');
          loadTasks();
          setPollingTasks((prev) => new Set([...prev, task.id]));
        } catch (err: any) {
          message.error(err.message || '重新运行任务失败');
        }
      },
    });
  };

  const columns = [
    {
      title: t('collection.taskId'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
      ellipsis: true,
    },
    {
      title: t('common.type'),
      dataIndex: 'type',
      key: 'type',
      width: 150,
    },
    {
      title: t('collection.status'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: t('collection.progress'),
      dataIndex: 'progress',
      key: 'progress',
      width: 200,
      render: (progress: number, record: Task) => (
        <Progress percent={progress} status={record.status === TaskStatus.FAILED ? 'exception' : 'active'} />
      ),
    },
    {
      title: t('common.message'),
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: t('collection.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
    {
      title: t('collection.actions'),
      key: 'action',
      width: 220,
      fixed: 'right' as const,
      render: (_: any, record: Task) => {
        const isEdited = editedTasks.has(record.id);
        const hasRun = record.status === TaskStatus.COMPLETED || record.status === TaskStatus.FAILED;
        const isRunning = record.status === TaskStatus.RUNNING;
        
        return (
          <Space size="small">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditTask(record)}
              disabled={isRunning}
            >
              {t('collection.editTask')}
            </Button>
            {/* 如果任务被编辑过且未运行，显示启动按钮 */}
            {isEdited && !hasRun && (
              <Button
                type="link"
                size="small"
                icon={<CaretRightOutlined />}
                onClick={() => handleStartTask(record)}
                disabled={isRunning}
              >
                {t('common.start')}
              </Button>
            )}
            {/* 如果任务已运行过，显示重跑按钮 */}
            {hasRun && (
              <Button
                type="link"
                size="small"
                icon={<RedoOutlined />}
                onClick={() => handleRerunTask(record)}
                disabled={isRunning}
              >
                {t('common.rerun')}
              </Button>
            )}
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteTask(record.id)}
              disabled={isRunning}
            >
              {t('collection.deleteTask')}
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <Card
        title={t('collection.title')}
        extra={
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            {t('collection.createTask')}
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ReloadOutlined />} onClick={loadTasks}>
            {t('common.refresh')}
          </Button>
          <Button 
            icon={<HistoryOutlined />} 
            onClick={() => setShowHistory(!showHistory)}
            type={showHistory ? 'primary' : 'default'}
          >
            {showHistory ? t('common.hideHistory') : t('common.showHistory')}
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={tasks}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* 任务执行历史列表 */}
      {showHistory && (
        <Card 
          title="任务执行历史" 
          style={{ marginTop: 16 }}
          extra={
            <Button size="small" onClick={() => setShowHistory(false)}>
              关闭
            </Button>
          }
        >
          <Table
            columns={[
              {
                title: '任务ID',
                dataIndex: 'id',
                key: 'id',
                width: 200,
                ellipsis: true,
              },
              {
                title: '类型',
                dataIndex: 'type',
                key: 'type',
                width: 150,
              },
              {
                title: '状态',
                dataIndex: 'status',
                key: 'status',
                width: 100,
                render: (status: string) => getStatusTag(status),
              },
              {
                title: '实体数量',
                key: 'entities_count',
                width: 100,
                render: (_: any, record: Task) => record.result?.entities_count || 0,
              },
              {
                title: '关系数量',
                key: 'relationships_count',
                width: 100,
                render: (_: any, record: Task) => record.result?.relationships_count || 0,
              },
              {
                title: '存储实体数',
                key: 'stored_entities',
                width: 100,
                render: (_: any, record: Task) => record.result?.stored_entities || 0,
              },
              {
                title: '存储关系数',
                key: 'stored_relationships',
                width: 100,
                render: (_: any, record: Task) => record.result?.stored_relationships || 0,
              },
              {
                title: '错误',
                key: 'errors',
                width: 150,
                render: (_: any, record: Task) => {
                  const errors = record.result?.errors || record.error;
                  if (!errors) return '-';
                  if (Array.isArray(errors)) {
                    return errors.length > 0 ? (
                      <Tag color="red">{errors.length} 个错误</Tag>
                    ) : '-';
                  }
                  return <Tag color="red">有错误</Tag>;
                },
              },
              {
                title: '开始时间',
                dataIndex: 'started_at',
                key: 'started_at',
                width: 180,
              },
              {
                title: '完成时间',
                dataIndex: 'completed_at',
                key: 'completed_at',
                width: 180,
              },
              {
                title: '消息',
                dataIndex: 'message',
                key: 'message',
                ellipsis: true,
              },
            ]}
            dataSource={tasks.filter(t => t.status === TaskStatus.COMPLETED || t.status === TaskStatus.FAILED)}
            loading={loading}
            rowKey="id"
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
            }}
          />
        </Card>
      )}

      <Modal
        title={t('collection.createTask')}
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
          setCollectorType('');
          setSelectedPackage('');
        }}
        onOk={() => form.submit()}
        width={700}
      >
        <Form form={form} onFinish={handleCreateTask} layout="vertical">
          <Form.Item
            name="package_name"
            label={t('collection.package')}
            tooltip={t('collection.selectPackage')}
          >
            <Select 
              placeholder={t('collection.selectPackage')}
              allowClear
              onChange={(value) => {
                setSelectedPackage(value || '');
                loadCollectorOptions(value || undefined);
                // 清空采集器类型选择
                form.setFieldsValue({ collector_type: undefined });
                setCollectorType('');
              }}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {packageOptions.map((option) => (
                <Option 
                  key={option.value} 
                  value={option.value}
                  label={option.label}
                >
                  {option.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            name="collector_type"
            label="采集器类型"
            rules={[{ required: true, message: '请选择采集器类型' }]}
          >
            <Select 
              placeholder="选择采集器类型"
              onChange={handleCollectorTypeChange}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {collectorOptions.map((option) => (
                <Option 
                  key={option.value} 
                  value={option.value}
                  label={option.label}
                >
                  {option.label}
                  {option.isMetamodel && (
                    <Tag color="purple" style={{ marginLeft: 8 }}>元模型</Tag>
                  )}
                  {option.packageName && (
                    <Tag color="blue" style={{ marginLeft: 4 }}>{option.packageName}</Tag>
                  )}
                </Option>
              ))}
            </Select>
          </Form.Item>

          {/* 关系型数据库配置（仅当不是元模型采集器时显示） */}
          {(() => {
            const collectorOption = collectorOptions.find(opt => opt.value === collectorType);
            return collectorType === 'relational' && (!collectorOption || !collectorOption.isMetamodel);
          })() && (
            <>
              <Form.Item
                name="db_type"
                label="数据库类型"
                initialValue="postgresql"
                rules={[{ required: true, message: '请选择数据库类型' }]}
              >
                <Select placeholder="选择数据库类型">
                  <Option value="postgresql">PostgreSQL</Option>
                  <Option value="mysql">MySQL</Option>
                  <Option value="sqlite">SQLite</Option>
                </Select>
              </Form.Item>
              <Form.Item
                name="host"
                label="主机地址"
                rules={[{ required: true, message: '请输入主机地址' }]}
              >
                <Input placeholder="localhost" />
              </Form.Item>
              <Form.Item
                name="port"
                label="端口"
                rules={[{ required: true, message: '请输入端口' }]}
              >
                <InputNumber placeholder="5432" style={{ width: '100%' }} min={1} max={65535} />
              </Form.Item>
              <Form.Item
                name="database"
                label="数据库名"
                rules={[{ required: true, message: '请输入数据库名' }]}
              >
                <Input placeholder="database_name" />
              </Form.Item>
              <Form.Item
                name="username"
                label="用户名"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input placeholder="username" />
              </Form.Item>
              <Form.Item
                name="password"
                label="密码"
                rules={[{ required: true, message: '请输入密码' }]}
              >
                <Input.Password placeholder="password" />
              </Form.Item>
              <Form.Item
                name="source"
                label="数据源标识"
                tooltip="可选，用于标识数据源"
              >
                <Input placeholder="relational_db" />
              </Form.Item>
            </>
          )}

          {/* 图数据库配置（仅当不是元模型采集器时显示） */}
          {(() => {
            const collectorOption = collectorOptions.find(opt => opt.value === collectorType);
            return collectorType === 'graphdb' && (!collectorOption || !collectorOption.isMetamodel);
          })() && (
            <>
              <Form.Item
                name="graphdb_type"
                label="图数据库类型"
                initialValue="neo4j"
                rules={[{ required: true, message: '请选择图数据库类型' }]}
              >
                <Select placeholder="选择图数据库类型">
                  <Option value="neo4j">Neo4j</Option>
                  <Option value="falkordb">FalkorDB</Option>
                </Select>
              </Form.Item>
              <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => 
                prevValues.graphdb_type !== currentValues.graphdb_type
              }>
                {({ getFieldValue }) => {
                  const dbType = getFieldValue('graphdb_type');
                  if (dbType === 'neo4j') {
                    return (
                      <>
                        <Form.Item
                          name="uri"
                          label="URI"
                          rules={[{ required: true, message: '请输入URI' }]}
                          initialValue="bolt://localhost:7687"
                        >
                          <Input placeholder="bolt://localhost:7687" />
                        </Form.Item>
                        <Form.Item
                          name="username"
                          label="用户名"
                          rules={[{ required: true, message: '请输入用户名' }]}
                          initialValue="neo4j"
                        >
                          <Input placeholder="neo4j" />
                        </Form.Item>
                        <Form.Item
                          name="password"
                          label="密码"
                          rules={[{ required: true, message: '请输入密码' }]}
                        >
                          <Input.Password placeholder="password" />
                        </Form.Item>
                      </>
                    );
                  } else if (dbType === 'falkordb') {
                    return (
                      <>
                        <Form.Item
                          name="host"
                          label="主机地址"
                          rules={[{ required: true, message: '请输入主机地址' }]}
                          initialValue="localhost"
                        >
                          <Input placeholder="localhost" />
                        </Form.Item>
                        <Form.Item
                          name="port"
                          label="端口"
                          rules={[{ required: true, message: '请输入端口' }]}
                          initialValue={6379}
                        >
                          <InputNumber placeholder="6379" style={{ width: '100%' }} min={1} max={65535} />
                        </Form.Item>
                        <Form.Item
                          name="password"
                          label="密码"
                        >
                          <Input.Password placeholder="password (可选)" />
                        </Form.Item>
                        <Form.Item
                          name="graph_name"
                          label="图名称"
                          rules={[{ required: true, message: '请输入图名称' }]}
                          initialValue="default"
                        >
                          <Input placeholder="default" />
                        </Form.Item>
                      </>
                    );
                  }
                  return null;
                }}
              </Form.Item>
              <Form.Item
                name="source"
                label="数据源标识"
                tooltip="可选，用于标识数据源"
              >
                <Input placeholder="graph_db" />
              </Form.Item>
            </>
          )}

          {/* 代码元数据配置（仅当不是元模型采集器时显示） */}
          {(() => {
            const collectorOption = collectorOptions.find(opt => opt.value === collectorType);
            return collectorType === 'code' && (!collectorOption || !collectorOption.isMetamodel);
          })() && (
            <>
              <Form.Item
                name="source_path"
                label="源代码路径"
                rules={[{ required: true, message: '请输入源代码路径' }]}
              >
                <Input placeholder="/path/to/code" />
              </Form.Item>
              <Form.Item
                name="languages"
                label="支持的语言"
                rules={[{ required: true, message: '请至少选择一种语言' }]}
                initialValue={['python']}
              >
                <Checkbox.Group>
                  <Checkbox value="python">Python</Checkbox>
                  <Checkbox value="javascript">JavaScript</Checkbox>
                  <Checkbox value="typescript">TypeScript</Checkbox>
                  <Checkbox value="java">Java</Checkbox>
                </Checkbox.Group>
              </Form.Item>
              <Form.Item
                name="source"
                label="数据源标识"
                tooltip="可选，用于标识数据源"
              >
                <Input placeholder="code" />
              </Form.Item>
              <Form.Item
                name="exclude_patterns"
                label="排除模式"
                tooltip="每行一个模式，例如: **/node_modules/**"
              >
                <TextArea 
                  rows={3} 
                  placeholder="**/node_modules/**&#10;**/__pycache__/**&#10;**/.git/**"
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
            </>
          )}

          {/* 文件系统配置（仅当不是元模型采集器时显示） */}
          {(() => {
            const collectorOption = collectorOptions.find(opt => opt.value === collectorType);
            // 只有当采集器类型是 'filesystem' 且不是元模型采集器时才显示
            // 如果 collectorOption 不存在，说明可能是系统内置的采集器
            return collectorType === 'filesystem' && (!collectorOption || !collectorOption.isMetamodel);
          })() && (
            <>
              <Form.Item
                name="scan_paths"
                label="扫描路径"
                rules={[{ required: true, message: '请输入至少一个扫描路径' }]}
                tooltip="多个路径用换行分隔"
              >
                <TextArea 
                  rows={3} 
                  placeholder="/path/to/scan1&#10;/path/to/scan2"
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
              <Form.Item
                name="source"
                label="数据源标识"
                tooltip="可选，用于标识数据源"
              >
                <Input placeholder="filesystem" />
              </Form.Item>
              <Form.Item
                name="exclude_patterns"
                label="排除模式"
                tooltip="每行一个模式，例如: **/.git/**"
              >
                <TextArea 
                  rows={3} 
                  placeholder="**/.git/**&#10;**/node_modules/**"
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
              <Form.Item
                name="max_depth"
                label="最大深度"
                tooltip="可选，限制扫描深度"
              >
                <InputNumber placeholder="无限制" style={{ width: '100%' }} min={1} />
              </Form.Item>
            </>
          )}

          {/* 元模型采集器动态配置（根据config_schema生成） */}
          {(() => {
            const collectorOption = collectorOptions.find(opt => opt.value === collectorType);
            // 如果是元模型采集器且有配置schema，显示动态配置表单
            if (collectorOption?.isMetamodel) {
              if (collectorOption.configSchema && collectorOption.configSchema.length > 0) {
                return renderConfigFields(collectorOption.configSchema, form);
              } else {
                // 如果没有configSchema，尝试从API重新获取
                console.warn(`元模型采集器 ${collectorType} 没有配置schema`);
              }
            }
            return null;
          })()}
        </Form>
      </Modal>

      {/* 编辑任务模态框 */}
      <Modal
        title={t('collection.editTask')}
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
          setEditingTask(null);
          setEditCollectorType('');
        }}
        onOk={() => editForm.submit()}
        width={700}
      >
        <Form form={editForm} onFinish={handleUpdateTask} layout="vertical">
          <Form.Item
            name="collector_type"
            label="采集器类型"
            rules={[{ required: true, message: '请选择采集器类型' }]}
          >
            <Select 
              placeholder="选择采集器类型"
              onChange={handleEditCollectorTypeChange}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {collectorOptions.map((option) => (
                <Option 
                  key={option.value} 
                  value={option.value}
                  label={option.label}
                >
                  {option.label}
                  {option.isMetamodel && (
                    <Tag color="purple" style={{ marginLeft: 8 }}>元模型</Tag>
                  )}
                </Option>
              ))}
            </Select>
          </Form.Item>

          {/* 关系型数据库配置 */}
          {editCollectorType === 'relational' && (
            <>
              <Form.Item
                name="db_type"
                label="数据库类型"
                rules={[{ required: true, message: '请选择数据库类型' }]}
              >
                <Select placeholder="选择数据库类型">
                  <Option value="postgresql">PostgreSQL</Option>
                  <Option value="mysql">MySQL</Option>
                  <Option value="sqlite">SQLite</Option>
                </Select>
              </Form.Item>
              <Form.Item
                name="host"
                label="主机地址"
                rules={[{ required: true, message: '请输入主机地址' }]}
              >
                <Input placeholder="localhost" />
              </Form.Item>
              <Form.Item
                name="port"
                label="端口"
                rules={[{ required: true, message: '请输入端口' }]}
              >
                <InputNumber placeholder="5432" style={{ width: '100%' }} min={1} max={65535} />
              </Form.Item>
              <Form.Item
                name="database"
                label="数据库名"
                rules={[{ required: true, message: '请输入数据库名' }]}
              >
                <Input placeholder="database_name" />
              </Form.Item>
              <Form.Item
                name="username"
                label="用户名"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input placeholder="username" />
              </Form.Item>
              <Form.Item
                name="password"
                label="密码"
                rules={[{ required: true, message: '请输入密码' }]}
              >
                <Input.Password placeholder="password" />
              </Form.Item>
              <Form.Item
                name="source"
                label="数据源标识"
                tooltip="可选，用于标识数据源"
              >
                <Input placeholder="relational_db" />
              </Form.Item>
            </>
          )}

          {/* 图数据库配置 */}
          {editCollectorType === 'graphdb' && (
            <>
              <Form.Item
                name="graphdb_type"
                label="图数据库类型"
                rules={[{ required: true, message: '请选择图数据库类型' }]}
              >
                <Select placeholder="选择图数据库类型">
                  <Option value="neo4j">Neo4j</Option>
                  <Option value="falkordb">FalkorDB</Option>
                </Select>
              </Form.Item>
              <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => 
                prevValues.graphdb_type !== currentValues.graphdb_type
              }>
                {({ getFieldValue }) => {
                  const dbType = getFieldValue('graphdb_type');
                  if (dbType === 'neo4j') {
                    return (
                      <>
                        <Form.Item
                          name="uri"
                          label="URI"
                          rules={[{ required: true, message: '请输入URI' }]}
                        >
                          <Input placeholder="bolt://localhost:7687" />
                        </Form.Item>
                        <Form.Item
                          name="username"
                          label="用户名"
                          rules={[{ required: true, message: '请输入用户名' }]}
                        >
                          <Input placeholder="neo4j" />
                        </Form.Item>
                        <Form.Item
                          name="password"
                          label="密码"
                          rules={[{ required: true, message: '请输入密码' }]}
                        >
                          <Input.Password placeholder="password" />
                        </Form.Item>
                      </>
                    );
                  } else if (dbType === 'falkordb') {
                    return (
                      <>
                        <Form.Item
                          name="host"
                          label="主机地址"
                          rules={[{ required: true, message: '请输入主机地址' }]}
                        >
                          <Input placeholder="localhost" />
                        </Form.Item>
                        <Form.Item
                          name="port"
                          label="端口"
                          rules={[{ required: true, message: '请输入端口' }]}
                        >
                          <InputNumber placeholder="6379" style={{ width: '100%' }} min={1} max={65535} />
                        </Form.Item>
                        <Form.Item
                          name="password"
                          label="密码"
                        >
                          <Input.Password placeholder="password (可选)" />
                        </Form.Item>
                        <Form.Item
                          name="graph_name"
                          label="图名称"
                          rules={[{ required: true, message: '请输入图名称' }]}
                        >
                          <Input placeholder="default" />
                        </Form.Item>
                      </>
                    );
                  }
                  return null;
                }}
              </Form.Item>
              <Form.Item
                name="source"
                label="数据源标识"
                tooltip="可选，用于标识数据源"
              >
                <Input placeholder="graph_db" />
              </Form.Item>
            </>
          )}

          {/* 代码元数据配置 */}
          {editCollectorType === 'code' && (
            <>
              <Form.Item
                name="source_path"
                label="源代码路径"
                rules={[{ required: true, message: '请输入源代码路径' }]}
              >
                <Input placeholder="/path/to/code" />
              </Form.Item>
              <Form.Item
                name="languages"
                label="支持的语言"
                rules={[{ required: true, message: '请至少选择一种语言' }]}
              >
                <Checkbox.Group>
                  <Checkbox value="python">Python</Checkbox>
                  <Checkbox value="javascript">JavaScript</Checkbox>
                  <Checkbox value="typescript">TypeScript</Checkbox>
                  <Checkbox value="java">Java</Checkbox>
                </Checkbox.Group>
              </Form.Item>
              <Form.Item
                name="source"
                label="数据源标识"
                tooltip="可选，用于标识数据源"
              >
                <Input placeholder="code" />
              </Form.Item>
              <Form.Item
                name="exclude_patterns"
                label="排除模式"
                tooltip="每行一个模式，例如: **/node_modules/**"
              >
                <TextArea 
                  rows={3} 
                  placeholder="**/node_modules/**&#10;**/__pycache__/**&#10;**/.git/**"
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
            </>
          )}

          {/* 文件系统配置 */}
          {editCollectorType === 'filesystem' && (
            <>
              <Form.Item
                name="scan_paths"
                label="扫描路径"
                rules={[{ required: true, message: '请输入至少一个扫描路径' }]}
                tooltip="多个路径用换行分隔"
              >
                <TextArea 
                  rows={3} 
                  placeholder="/path/to/scan1&#10;/path/to/scan2"
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
              <Form.Item
                name="source"
                label="数据源标识"
                tooltip="可选，用于标识数据源"
              >
                <Input placeholder="filesystem" />
              </Form.Item>
              <Form.Item
                name="exclude_patterns"
                label="排除模式"
                tooltip="每行一个模式，例如: **/.git/**"
              >
                <TextArea 
                  rows={3} 
                  placeholder="**/.git/**&#10;**/node_modules/**"
                  style={{ fontFamily: 'monospace' }}
                />
              </Form.Item>
              <Form.Item
                name="max_depth"
                label="最大深度"
                tooltip="可选，限制扫描深度"
              >
                <InputNumber placeholder="无限制" style={{ width: '100%' }} min={1} />
              </Form.Item>
            </>
          )}

          {/* 元模型采集器动态配置（根据config_schema生成） */}
          {(() => {
            const collectorOption = collectorOptions.find(opt => opt.value === editCollectorType);
            if (collectorOption?.isMetamodel && collectorOption?.configSchema) {
              return renderConfigFields(collectorOption.configSchema, editForm);
            }
            return null;
          })()}
        </Form>
      </Modal>
    </div>
  );
}

