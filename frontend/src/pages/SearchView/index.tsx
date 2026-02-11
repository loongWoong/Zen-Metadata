/**
 * 搜索与语义检索页面
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Tag,
  Space,
  Switch,
  Select,
  Typography,
  Alert,
  Spin,
  Descriptions,
  Row,
  Col,
  Slider,
} from 'antd';
import { SearchOutlined, StarOutlined, LinkOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import type { MetadataEntity } from '../../types';

const { Title, Text } = Typography;

interface SearchResult {
  entity: MetadataEntity;
  score: number;
  match_type: string;
  highlights?: string[];
}

const SearchView: React.FC = () => {
  const { t } = useTranslation();
  const [query, setQuery] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [entityType, setEntityType] = useState<string>('');
  const [source, setSource] = useState<string>('');
  const [useSemantic, setUseSemantic] = useState<boolean>(false);
  const [useGraph, setUseGraph] = useState<boolean>(true);
  const [limit, setLimit] = useState<number>(50);
  const [minQuality, setMinQuality] = useState<number>(0);
  const [entityTypes, setEntityTypes] = useState<string[]>([]);
  const [sources, setSources] = useState<string[]>([]);

  // 执行搜索
  const handleSearch = async () => {
    if (!query.trim()) {
      return;
    }

    setLoading(true);
    try {
      const response = await api.search.search({
        q: query,
        entity_type: entityType || undefined,
        source: source || undefined,
        limit,
        use_semantic: useSemantic,
        use_graph: useGraph,
      });
      setResults(response.data.results || []);
    } catch (error: any) {
      console.error(t('search.searchFailed'), error);
    } finally {
      setLoading(false);
    }
  };

  // 语义搜索
  const handleSemanticSearch = async () => {
    if (!query.trim()) {
      return;
    }

    setLoading(true);
    try {
      const response = await api.search.semantic({
        q: query,
        entity_type: entityType || undefined,
        source: source || undefined,
        limit,
      });
      setResults(response.data.results || []);
    } catch (error: any) {
      console.error(t('search.semanticSearchFailed'), error);
    } finally {
      setLoading(false);
    }
  };

  // 带质量过滤的搜索
  const handleQualitySearch = async () => {
    if (!query.trim()) {
      return;
    }

    setLoading(true);
    try {
      const response = await api.search.searchWithQuality({
        q: query,
        entity_type: entityType || undefined,
        source: source || undefined,
        limit,
        min_quality: minQuality,
      });
      setResults(response.data.results || []);
    } catch (error: any) {
      console.error(t('search.qualitySearchFailed'), error);
    } finally {
      setLoading(false);
    }
  };

  // 获取推荐
  const handleGetRecommendations = async (entityId: string) => {
    setLoading(true);
    try {
      const response = await api.search.recommend(entityId, 10);
      setResults(response.data.recommendations || []);
    } catch (error: any) {
      console.error(t('search.getRecommendationsFailed'), error);
    } finally {
      setLoading(false);
    }
  };

  // 加载实体类型
  const loadEntityTypes = async () => {
    try {
      const response = await api.statistics.entityDistribution();
      if (response.data?.data) {
        const types = response.data.data.map((item: any) => item.type).filter(Boolean);
        setEntityTypes(types);
      } else {
        const entitiesResponse = await api.entities.list({ limit: 1000 });
        const types = new Set<string>();
        entitiesResponse.data.entities.forEach((entity: any) => {
          if (entity.type) {
            types.add(entity.type);
          }
        });
        setEntityTypes(Array.from(types));
      }
    } catch (err: any) {
      console.error(t('search.loadEntityTypesFailed'), err);
      setEntityTypes(['file', 'directory', 'function', 'class', 'table', 'column']);
    }
  };

  // 加载数据源
  const loadSources = async () => {
    try {
      const entitiesResponse = await api.entities.list({ limit: 1000 });
      const sourcesSet = new Set<string>();
      entitiesResponse.data.entities.forEach((entity: any) => {
        if (entity.source) {
          sourcesSet.add(entity.source);
        }
      });
      setSources(Array.from(sourcesSet).sort());
    } catch (err: any) {
      console.error(t('search.loadSourcesFailed'), err);
      setSources([]);
    }
  };

  useEffect(() => {
    loadEntityTypes();
    loadSources();
  }, []);

  // 表格列
  const columns = [
    {
      title: t('search.columns.entityId'),
      dataIndex: ['entity', 'id'],
      key: 'id',
      width: 200,
    },
    {
      title: t('search.columns.name'),
      dataIndex: ['entity', 'name'],
      key: 'name',
      width: 200,
    },
    {
      title: t('search.columns.type'),
      dataIndex: ['entity', 'type'],
      key: 'type',
      width: 120,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: t('search.columns.source'),
      dataIndex: ['entity', 'source'],
      key: 'source',
      width: 150,
    },
    {
      title: t('search.columns.matchType'),
      dataIndex: 'match_type',
      key: 'match_type',
      width: 120,
      render: (type: string) => {
        const colorMap: Record<string, string> = {
          text: 'blue',
          semantic: 'green',
          graph: 'orange',
        };
        return <Tag color={colorMap[type] || 'default'}>{type}</Tag>;
      },
    },
    {
      title: t('search.columns.score'),
      dataIndex: 'score',
      key: 'score',
      width: 100,
      render: (score: number) => (
        <Tag color={score > 5 ? 'green' : score > 2 ? 'orange' : 'default'}>
          {score.toFixed(2)}
        </Tag>
      ),
      sorter: (a: SearchResult, b: SearchResult) => a.score - b.score,
    },
    {
      title: t('search.columns.highlights'),
      dataIndex: 'highlights',
      key: 'highlights',
      render: (highlights: string[]) =>
        highlights && highlights.length > 0 ? (
          <Space direction="vertical" size="small">
            {highlights.slice(0, 2).map((h, idx) => (
              <Text key={idx} type="secondary" style={{ fontSize: '12px' }}>
                {h}
              </Text>
            ))}
          </Space>
        ) : null,
    },
    {
      title: t('search.columns.actions'),
      key: 'action',
      width: 150,
      render: (_: any, record: SearchResult) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<LinkOutlined />}
            onClick={() => handleGetRecommendations(record.entity.id)}
          >
            {t('search.recommend')}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>{t('search.title')}</Title>

      <Card style={{ marginBottom: '24px' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Input
            placeholder={t('search.searchPlaceholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onPressEnter={handleSearch}
            size="large"
            prefix={<SearchOutlined />}
            style={{ width: '100%' }}
          />

          <Row gutter={16}>
            <Col span={6}>
              <Text>{t('search.entityType')}:</Text>
              <Select
                placeholder={t('search.selectEntityType')}
                value={entityType}
                onChange={setEntityType}
                style={{ width: '100%', marginTop: '8px' }}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
              >
                {entityTypes.map((type) => (
                  <Select.Option key={type} value={type} label={type}>
                    {type}
                  </Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={6}>
              <Text>{t('search.source')}:</Text>
              <Select
                placeholder={t('search.selectSource')}
                value={source}
                onChange={setSource}
                style={{ width: '100%', marginTop: '8px' }}
                allowClear
                showSearch
                notFoundContent={sources.length === 0 ? t('search.loading') : t('search.noData')}
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
              >
                {sources.map((src) => (
                  <Select.Option key={src} value={src} label={src}>
                    {src}
                  </Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={6}>
              <Text>{t('search.resultCount')}:</Text>
              <Slider
                min={10}
                max={500}
                value={limit}
                onChange={setLimit}
                style={{ marginTop: '8px' }}
              />
              <Text type="secondary">{limit}</Text>
            </Col>
            <Col span={6}>
              <Space direction="vertical">
                <Space>
                  <Text>{t('search.semanticSearch')}:</Text>
                  <Switch checked={useSemantic} onChange={setUseSemantic} />
                </Space>
                <Space>
                  <Text>{t('search.graphRecommendation')}:</Text>
                  <Switch checked={useGraph} onChange={setUseGraph} />
                </Space>
              </Space>
            </Col>
          </Row>

          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch} loading={loading}>
              {t('search.comprehensiveSearch')}
            </Button>
            <Button icon={<StarOutlined />} onClick={handleSemanticSearch} loading={loading}>
              {t('search.semanticSearchButton')}
            </Button>
            <Button onClick={handleQualitySearch} loading={loading}>
              {t('search.qualityFilterSearch')}
            </Button>
            <Text>{t('search.minQuality')}:</Text>
            <Slider
              min={0}
              max={1}
              step={0.1}
              value={minQuality}
              onChange={setMinQuality}
              style={{ width: '150px' }}
            />
            <Text type="secondary">{(minQuality * 100).toFixed(0)}%</Text>
          </Space>
        </Space>
      </Card>

      <Spin spinning={loading}>
        {results.length > 0 ? (
          <Card>
            <Descriptions title={t('search.searchResults')} bordered column={2} style={{ marginBottom: '16px' }}>
              <Descriptions.Item label={t('search.query')}>{query}</Descriptions.Item>
              <Descriptions.Item label={t('search.resultCountLabel')}>{results.length}</Descriptions.Item>
              <Descriptions.Item label={t('search.useSemanticSearch')}>{useSemantic ? t('common.yes') : t('common.no')}</Descriptions.Item>
              <Descriptions.Item label={t('search.useGraphRecommendation')}>{useGraph ? t('common.yes') : t('common.no')}</Descriptions.Item>
            </Descriptions>

            <Table
              dataSource={results}
              columns={columns}
              rowKey={(record) => record.entity.id}
              pagination={{ pageSize: 20 }}
            />
          </Card>
        ) : (
          <Alert message={t('search.noResults')} type="info" />
        )}
      </Spin>
    </div>
  );
};

export default SearchView;


