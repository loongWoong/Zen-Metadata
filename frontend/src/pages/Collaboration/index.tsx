/**
 * 协作功能页面
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  List,
  Input,
  Button,
  Form,
  Tag,
  Space,
  message,
  Modal,
  Select,
  Table,
  Badge,
} from 'antd';
import {
  CommentOutlined,
  TagOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const { TextArea } = Input;
const { Option } = Select;

interface Comment {
  id: string;
  entity_id: string;
  user_id: string;
  content: string;
  parent_id?: string;
  version?: number;
  mentions: string[];
  created_at: string;
  updated_at: string;
}

interface Annotation {
  id: string;
  entity_id: string;
  user_id: string;
  tag: string;
  note: string;
  category?: string;
  created_at: string;
}

interface Approval {
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
}

const Collaboration: React.FC<{ entityId?: string }> = ({ entityId }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('comments');
  const [comments, setComments] = useState<Comment[]>([]);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);
  const [commentForm] = Form.useForm();
  const [annotationForm] = Form.useForm();
  const [approvalModalVisible, setApprovalModalVisible] = useState(false);
  const [approvalForm] = Form.useForm();

  useEffect(() => {
    if (entityId) {
      loadComments();
      loadAnnotations();
      loadApprovals();
    }
  }, [entityId]);

  const loadComments = async () => {
    if (!entityId) return;
    try {
      const response = await api.collaboration.getComments({ entity_id: entityId });
      setComments(response.data.comments);
    } catch (error) {
      console.error('加载评论失败:', error);
    }
  };

  const loadAnnotations = async () => {
    if (!entityId) return;
    try {
      const response = await api.collaboration.getAnnotations({ entity_id: entityId });
      setAnnotations(response.data.annotations);
    } catch (error) {
      console.error('加载标注失败:', error);
    }
  };

  const loadApprovals = async () => {
    if (!entityId) return;
    try {
      const response = await api.collaboration.getApprovals({ entity_id: entityId });
      setApprovals(response.data.approvals);
    } catch (error) {
      console.error('加载审批失败:', error);
    }
  };

  const handleAddComment = async (values: { content: string }) => {
    if (!entityId) return;
    setLoading(true);
    try {
      await api.collaboration.createComment({
        entity_id: entityId,
        content: values.content,
      });
      message.success(t('collaboration.commentAdded'));
      commentForm.resetFields();
      loadComments();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('collaboration.addCommentFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleAddAnnotation = async (values: {
    tag: string;
    note: string;
    category?: string;
  }) => {
    if (!entityId) return;
    setLoading(true);
    try {
      await api.collaboration.createAnnotation({
        entity_id: entityId,
        ...values,
      });
      message.success(t('collaboration.annotationAdded'));
      annotationForm.resetFields();
      loadAnnotations();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('collaboration.addAnnotationFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApproval = async (values: {
    change_type: string;
    change_data: any;
    level: string;
  }) => {
    if (!entityId) return;
    setLoading(true);
    try {
      await api.collaboration.createApproval({
        entity_id: entityId,
        ...values,
      });
      message.success(t('collaboration.approvalCreated'));
      approvalForm.resetFields();
      setApprovalModalVisible(false);
      loadApprovals();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('collaboration.createApprovalFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approvalId: string) => {
    try {
      await api.collaboration.approve(approvalId);
      message.success(t('common.approved'));
      loadApprovals();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('collaboration.operationFailed'));
    }
  };

  const handleReject = async (approvalId: string) => {
    try {
      await api.collaboration.reject(approvalId);
      message.success(t('common.rejected'));
      loadApprovals();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('collaboration.operationFailed'));
    }
  };

  const approvalColumns = [
    {
      title: t('collaboration.changeType'),
      dataIndex: 'change_type',
      key: 'change_type',
    },
    {
      title: t('collaboration.approvalLevel'),
      dataIndex: 'level',
      key: 'level',
    },
    {
      title: t('common.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          pending: { color: 'processing', text: t('common.pending') },
          approved: { color: 'success', text: t('common.approved') },
          rejected: { color: 'error', text: t('common.rejected') },
          cancelled: { color: 'default', text: t('collaboration.cancelled') },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Badge status={config.color as any} text={config.text} />;
      },
    },
    {
      title: t('common.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: t('common.actions'),
      key: 'action',
      render: (_: any, record: Approval) => (
        <Space>
          {record.status === 'pending' && (
            <>
              <Button
                type="link"
                icon={<CheckCircleOutlined />}
                onClick={() => handleApprove(record.id)}
              >
                {t('collaboration.approve')}
              </Button>
              <Button
                type="link"
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => handleReject(record.id)}
              >
                {t('collaboration.reject')}
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card title={t('collaboration.title')}>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'comments',
            label: (
              <span>
                <CommentOutlined /> {t('collaboration.comments')}
              </span>
            ),
            children: (
              <div>
                <Form form={commentForm} onFinish={handleAddComment} layout="vertical">
                  <Form.Item
                    name="content"
                    rules={[{ required: true, message: t('collaboration.pleaseInputComment') }]}
                  >
                    <TextArea rows={3} placeholder={t('collaboration.addComment')} />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading}>
                      {t('collaboration.addComment')}
                    </Button>
                  </Form.Item>
                </Form>
                <List
                  dataSource={comments}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space>
                            <span>{item.user_id}</span>
                            <span style={{ color: '#999', fontSize: '12px' }}>
                              {new Date(item.created_at).toLocaleString()}
                            </span>
                          </Space>
                        }
                        description={item.content}
                      />
                    </List.Item>
                  )}
                />
              </div>
            ),
          },
          {
            key: 'annotations',
            label: (
              <span>
                <TagOutlined /> {t('collaboration.annotations')}
              </span>
            ),
            children: (
              <div>
                <Form form={annotationForm} onFinish={handleAddAnnotation} layout="vertical">
                  <Form.Item
                    name="tag"
                    rules={[{ required: true, message: t('collaboration.pleaseInputTag') }]}
                  >
                    <Input placeholder={t('collaboration.tag')} />
                  </Form.Item>
                  <Form.Item
                    name="note"
                    rules={[{ required: true, message: t('collaboration.pleaseInputNote') }]}
                  >
                    <TextArea rows={3} placeholder={t('collaboration.note')} />
                  </Form.Item>
                  <Form.Item name="category">
                    <Select placeholder={t('collaboration.categoryOptional')}>
                      <Option value="business_semantic">{t('collaboration.businessSemantic')}</Option>
                      <Option value="usage_note">{t('collaboration.usageNote')}</Option>
                      <Option value="risk_warning">{t('collaboration.riskWarning')}</Option>
                      <Option value="experience">{t('collaboration.experience')}</Option>
                    </Select>
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading}>
                      {t('collaboration.addAnnotation')}
                    </Button>
                  </Form.Item>
                </Form>
                <List
                  dataSource={annotations}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space>
                            <Tag color="blue">{item.tag}</Tag>
                            {item.category && (
                              <Tag color="default">{item.category}</Tag>
                            )}
                            <span style={{ color: '#999', fontSize: '12px' }}>
                              {new Date(item.created_at).toLocaleString()}
                            </span>
                          </Space>
                        }
                        description={item.note}
                      />
                    </List.Item>
                  )}
                />
              </div>
            ),
          },
          {
            key: 'approvals',
            label: (
              <span>
                <CheckCircleOutlined /> {t('collaboration.approvals')}
              </span>
            ),
            children: (
              <div>
                <Button
                  type="primary"
                  onClick={() => setApprovalModalVisible(true)}
                  style={{ marginBottom: 16 }}
                >
                  {t('collaboration.createApprovalRequest')}
                </Button>
                <Table
                  columns={approvalColumns}
                  dataSource={approvals}
                  rowKey="id"
                  pagination={false}
                />
                <Modal
                  title={t('collaboration.createApprovalRequest')}
                  open={approvalModalVisible}
                  onCancel={() => setApprovalModalVisible(false)}
                  footer={null}
                >
                  <Form form={approvalForm} onFinish={handleCreateApproval} layout="vertical">
                    <Form.Item
                      name="change_type"
                      rules={[{ required: true, message: t('collaboration.pleaseSelectChangeType') }]}
                    >
                      <Select placeholder={t('collaboration.changeType')}>
                        <Option value="create">{t('common.create')}</Option>
                        <Option value="update">{t('common.update')}</Option>
                        <Option value="delete">{t('common.delete')}</Option>
                      </Select>
                    </Form.Item>
                    <Form.Item
                      name="level"
                      rules={[{ required: true, message: t('collaboration.pleaseSelectApprovalLevel') }]}
                    >
                      <Select placeholder={t('collaboration.approvalLevel')}>
                        <Option value="technical">{t('collaboration.technicalApproval')}</Option>
                        <Option value="data_governance">{t('collaboration.dataGovernanceApproval')}</Option>
                        <Option value="business">{t('collaboration.businessApproval')}</Option>
                      </Select>
                    </Form.Item>
                    <Form.Item
                      name="change_data"
                      rules={[{ required: true, message: t('collaboration.pleaseInputChangeData') }]}
                    >
                      <TextArea rows={4} placeholder={t('collaboration.changeDataJson')} />
                    </Form.Item>
                    <Form.Item>
                      <Button type="primary" htmlType="submit" loading={loading} block>
                        {t('common.submit')}
                      </Button>
                    </Form.Item>
                  </Form>
                </Modal>
              </div>
            ),
          },
        ]}
      />
    </Card>
  );
};

export default Collaboration;



