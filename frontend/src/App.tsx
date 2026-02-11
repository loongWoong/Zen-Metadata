import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import enUS from 'antd/locale/en_US';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import MainLayout from './components/Layout/MainLayout';
import Dashboard from './pages/Dashboard';
import GraphView from './pages/GraphView';
import EntityBrowser from './pages/EntityBrowser';
import Collection from './pages/Collection';
import Analytics from './pages/Analytics';
import QualityManagement from './pages/QualityManagement';
import MetamodelManagement from './pages/MetamodelManagement';
import MetamodelGraph from './pages/MetamodelGraph';
import LineageView from './pages/LineageView';
import SearchView from './pages/SearchView';
import VersionControl from './pages/VersionControl';
import Login from './pages/Login';
import UserManagement from './pages/UserManagement';
import Collaboration from './pages/Collaboration';
import TagManagement from './pages/TagManagement';
import StandardManagement from './pages/StandardManagement';
import CatalogDiscovery from './pages/CatalogDiscovery';
import AgentManagement from './pages/AgentManagement';
import RoleManagement from './pages/RoleManagement';
import MenuManagement from './pages/MenuManagement';
import APIManagement from './pages/APIManagement';
import APITokenManagement from './pages/APITokenManagement';
import './App.css';

const { Content } = Layout;

// 路由保护组件
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function AppContent() {
  const { i18n } = useTranslation();
  const [locale, setLocale] = useState(i18n.language === 'zh-CN' ? zhCN : enUS);

  useEffect(() => {
    const handleLanguageChange = (lng: string) => {
      setLocale(lng === 'zh-CN' ? zhCN : enUS);
    };

    i18n.on('languageChanged', handleLanguageChange);
    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, [i18n]);

  const handleLanguageChange = (language: string) => {
    setLocale(language === 'zh-CN' ? zhCN : enUS);
  };

  return (
    <ConfigProvider locale={locale}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <MainLayout onLanguageChange={handleLanguageChange}>
                  <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/graph" element={<GraphView />} />
                    <Route path="/entities" element={<EntityBrowser />} />
                    <Route path="/collection" element={<Collection />} />
                    <Route path="/analytics" element={<Analytics />} />
                    <Route path="/quality" element={<QualityManagement />} />
                    <Route path="/metamodel" element={<MetamodelManagement />} />
                    <Route path="/metamodel-graph" element={<MetamodelGraph />} />
                    <Route path="/lineage" element={<LineageView />} />
                    <Route path="/search" element={<SearchView />} />
                    <Route path="/version" element={<VersionControl />} />
                    <Route path="/users" element={<UserManagement />} />
                    <Route path="/collaboration" element={<Collaboration />} />
                    <Route path="/governance/tags" element={<TagManagement />} />
                    <Route path="/governance/standards" element={<StandardManagement />} />
                    <Route path="/governance/catalog" element={<CatalogDiscovery />} />
                    <Route path="/agents" element={<AgentManagement />} />
                    <Route path="/roles" element={<RoleManagement />} />
                    <Route path="/menus" element={<MenuManagement />} />
                    <Route path="/api-management" element={<APIManagement />} />
                    <Route path="/api-tokens" element={<APITokenManagement />} />
                  </Routes>
                </MainLayout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

function App() {
  return <AppContent />;
}

export default App;
