import { Layout, Menu, theme, Dropdown, Avatar, Button, Space, Drawer } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import i18n from '../../i18n/config';
import logoImage from '../../assets/logo.png';
import {
  DashboardOutlined,
  NodeIndexOutlined,
  DatabaseOutlined,
  CloudUploadOutlined,
  BarChartOutlined,
  SafetyOutlined,
  ApartmentOutlined,
  ShareAltOutlined,
  SearchOutlined,
  HistoryOutlined,
  UserOutlined,
  LogoutOutlined,
  TeamOutlined,
  CommentOutlined,
  TagsOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  MenuOutlined,
  CloudServerOutlined,
  SettingOutlined,
  ApiOutlined,
  KeyOutlined,
  AppstoreOutlined,
  ControlOutlined,
  BookOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import type { ReactNode } from 'react';
import { useState, useEffect, useMemo } from 'react';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;

interface MainLayoutProps {
  children: ReactNode;
  onLanguageChange?: (language: string) => void;
}

export default function MainLayout({ children, onLanguageChange }: MainLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();
  const [user, setUser] = useState<any>(null);
  const [mobileMenuVisible, setMobileMenuVisible] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [currentLanguage, setCurrentLanguage] = useState(i18n.language);

  // 动态生成菜单项
  const menuItems = useMemo<MenuProps['items']>(() => [
    {
      key: '/overview',
      icon: <AppstoreOutlined />,
      label: t('menu.overview'),
      children: [
        {
          key: '/dashboard',
          icon: <DashboardOutlined />,
          label: t('menu.dashboard'),
        },
        {
          key: '/graph',
          icon: <NodeIndexOutlined />,
          label: t('menu.graph'),
        },
        {
          key: '/analytics',
          icon: <BarChartOutlined />,
          label: t('menu.analytics'),
        },
      ],
    },
    {
      key: '/metadata',
      icon: <DatabaseOutlined />,
      label: t('menu.metadata'),
      children: [
        {
          key: '/entities',
          icon: <DatabaseOutlined />,
          label: t('menu.entities'),
        },
        {
          key: '/search',
          icon: <SearchOutlined />,
          label: t('menu.search'),
        },
        {
          key: '/lineage',
          icon: <ShareAltOutlined />,
          label: t('menu.lineage'),
        },
      ],
    },
    {
      key: '/collection',
      icon: <CloudUploadOutlined />,
      label: t('menu.collection'),
      children: [
        {
          key: '/collection',
          icon: <CloudUploadOutlined />,
          label: t('menu.collectionManagement'),
        },
        {
          key: '/agents',
          icon: <CloudServerOutlined />,
          label: t('menu.agents'),
        },
      ],
    },
    {
      key: '/quality',
      icon: <SafetyOutlined />,
      label: t('menu.quality'),
      children: [
        {
          key: '/quality',
          icon: <SafetyOutlined />,
          label: t('menu.qualityAssessment'),
        },
        {
          key: '/version',
          icon: <HistoryOutlined />,
          label: t('menu.version'),
        },
      ],
    },
    {
      key: '/governance',
      icon: <ControlOutlined />,
      label: t('menu.governance'),
      children: [
        {
          key: '/governance/tags',
          icon: <TagsOutlined />,
          label: t('menu.tags'),
        },
        {
          key: '/governance/standards',
          icon: <FileTextOutlined />,
          label: t('menu.standards'),
        },
        {
          key: '/governance/catalog',
          icon: <FolderOpenOutlined />,
          label: t('menu.catalog'),
        },
      ],
    },
    {
      key: '/collaboration',
      icon: <CommentOutlined />,
      label: t('menu.collaboration'),
      children: [
        {
          key: '/collaboration',
          icon: <CommentOutlined />,
          label: t('menu.collaborationDiscussion'),
        },
      ],
    },
    {
      key: '/configuration',
      icon: <SettingOutlined />,
      label: t('menu.configuration'),
      children: [
        {
          key: '/metamodel',
          icon: <ApartmentOutlined />,
          label: t('menu.metamodel'),
        },
        {
          key: '/metamodel-graph',
          icon: <ApartmentOutlined />,
          label: t('menu.metamodelGraph'),
        },
      ],
    },
    {
      key: '/system',
      icon: <BookOutlined />,
      label: t('menu.system'),
      children: [
        {
          key: '/users',
          icon: <UserOutlined />,
          label: t('menu.users'),
        },
        {
          key: '/roles',
          icon: <TeamOutlined />,
          label: t('menu.roles'),
        },
        {
          key: '/menus',
          icon: <MenuOutlined />,
          label: t('menu.menus'),
        },
        {
          key: '/api-management',
          icon: <ApiOutlined />,
          label: t('menu.apiManagement'),
        },
        {
          key: '/api-tokens',
          icon: <KeyOutlined />,
          label: t('menu.apiTokens'),
        },
      ],
    },
  ], [t]);

  useEffect(() => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      setUser(JSON.parse(userStr));
    }

    // 检测移动端
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 监听语言变化
  useEffect(() => {
    const handleLanguageChange = (lng: string) => {
      setCurrentLanguage(lng);
      if (onLanguageChange) {
        onLanguageChange(lng);
      }
    };

    i18n.on('languageChanged', handleLanguageChange);
    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, [onLanguageChange]);

  const handleLanguageSwitch = () => {
    const newLanguage = currentLanguage === 'zh-CN' ? 'en-US' : 'zh-CN';
    i18n.changeLanguage(newLanguage);
    localStorage.setItem('language', newLanguage);
    setCurrentLanguage(newLanguage);
    if (onLanguageChange) {
      onLanguageChange(newLanguage);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: t('common.logout'),
      onClick: handleLogout,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh', width: '100%' }}>
      {isMobile ? (
        <>
          <Header
            style={{
              padding: '0 16px',
              background: colorBgContainer,
              borderBottom: '1px solid #f0f0f0',
              position: 'sticky',
              top: 0,
              zIndex: 1,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setMobileMenuVisible(true)}
            />
            <img
              src={logoImage}
              alt="Zen Metadata"
              style={{
                height: '32px',
                width: 'auto',
                objectFit: 'contain',
              }}
            />
            <Space>
              <Button
                type="text"
                icon={<GlobalOutlined />}
                onClick={handleLanguageSwitch}
                style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                {currentLanguage === 'zh-CN' ? t('common.english') : t('common.chinese')}
              </Button>
              {user && (
                <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                  <Avatar icon={<UserOutlined />} />
                </Dropdown>
              )}
            </Space>
          </Header>
          <Drawer
            title={t('common.menu')}
            placement="left"
            onClose={() => setMobileMenuVisible(false)}
            open={mobileMenuVisible}
            bodyStyle={{ padding: 0 }}
          >
            <Menu
              mode="inline"
              selectedKeys={[location.pathname]}
              items={menuItems}
              onClick={({ key }) => {
                navigate(key);
                setMobileMenuVisible(false);
              }}
            />
          </Drawer>
        </>
      ) : (
        <Sider theme="light" width={200} style={{ position: 'fixed', left: 0, top: 0, bottom: 0 }}>
          <div
            style={{
              height: 64,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderBottom: '1px solid #f0f0f0',
              padding: '8px 16px',
            }}
          >
            <img
              src={logoImage}
              alt="Zen Metadata"
              style={{
                height: '48px',
                width: 'auto',
                objectFit: 'contain',
              }}
            />
          </div>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ 
              height: 'calc(100vh - 64px)', 
              borderRight: 0,
              overflowY: 'auto',
              overflowX: 'hidden'
            }}
          />
        </Sider>
      )}
      <Layout style={{ marginLeft: isMobile ? 0 : 200 }}>
        {!isMobile && (
          <Header
            style={{
              padding: '0 24px',
              background: colorBgContainer,
              borderBottom: '1px solid #f0f0f0',
              position: 'sticky',
              top: 0,
              zIndex: 1,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ fontSize: 20, fontWeight: 'bold' }}>{t('common.systemTitle')}</div>
            </div>
            <Space>
              <Button
                type="text"
                icon={<GlobalOutlined />}
                onClick={handleLanguageSwitch}
                style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                {currentLanguage === 'zh-CN' ? t('common.english') : t('common.chinese')}
              </Button>
              {user && (
                <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                  <Space style={{ cursor: 'pointer' }}>
                    <Avatar icon={<UserOutlined />} />
                    <span>{user.username}</span>
                  </Space>
                </Dropdown>
              )}
            </Space>
          </Header>
        )}
        <Content
          style={{
            margin: isMobile ? '8px' : '24px',
            padding: isMobile ? 16 : 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}

