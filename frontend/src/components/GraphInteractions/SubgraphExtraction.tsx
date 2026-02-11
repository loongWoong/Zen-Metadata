/**
 * 子图提取组件
 * 一键保存关注范围，用于讨论、评审、汇报
 */
import { useState } from 'react';
import { Button, Modal, Input, message, Space } from 'antd';
import { SaveOutlined, ShareAltOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { GraphData } from '../../types';

interface SubgraphExtractionProps {
  data: GraphData;
  onSave?: (name: string, subgraph: GraphData) => void;
  onShare?: (subgraph: GraphData) => void;
}

export default function SubgraphExtraction({ data, onSave, onShare }: SubgraphExtractionProps) {
  const { t } = useTranslation();
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [subgraphName, setSubgraphName] = useState('');

  const handleSave = () => {
    if (!subgraphName.trim()) {
      message.warning(t('components.subgraphExtraction.inputSubgraphName'));
      return;
    }

    onSave?.(subgraphName, data);
    message.success(t('components.subgraphExtraction.subgraphSaved'));
    setSaveModalVisible(false);
    setSubgraphName('');
  };

  const handleShare = () => {
    // 导出为JSON
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `subgraph_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(t('components.subgraphExtraction.subgraphExported'));
  };

  return (
    <>
      <Space size="small" style={{ flexShrink: 0 }}>
        <Button size="small" icon={<SaveOutlined />} onClick={() => setSaveModalVisible(true)}>
          {t('components.subgraphExtraction.saveSubgraph')}
        </Button>
        <Button size="small" icon={<ShareAltOutlined />} onClick={handleShare}>
          {t('components.subgraphExtraction.exportSubgraph')}
        </Button>
      </Space>
      <Modal
        title={t('components.subgraphExtraction.saveSubgraphTitle')}
        open={saveModalVisible}
        onOk={handleSave}
        onCancel={() => {
          setSaveModalVisible(false);
          setSubgraphName('');
        }}
      >
        <Input
          placeholder={t('components.subgraphExtraction.subgraphNamePlaceholder')}
          value={subgraphName}
          onChange={(e) => setSubgraphName(e.target.value)}
          onPressEnter={handleSave}
        />
      </Modal>
    </>
  );
}


