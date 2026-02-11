/**
 * 登录页面
 */
import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Tabs } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const Login: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('login');

  const onLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const response = await api.auth.login(values);
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      message.success(t('login.loginSuccess'));
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('login.loginFailed'));
    } finally {
      setLoading(false);
    }
  };

  const onRegister = async (values: {
    username: string;
    email?: string;
    password: string;
  }) => {
    setLoading(true);
    try {
      const response = await api.auth.register(values);
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      message.success(t('login.registerSuccess'));
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('login.registerFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Card style={{ width: 400, boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'login',
              label: t('login.title'),
              children: (
                <Form onFinish={onLogin} layout="vertical">
                  <Form.Item
                    name="username"
                    rules={[{ required: true, message: t('login.pleaseInputUsername') }]}
                  >
                    <Input
                      prefix={<UserOutlined />}
                      placeholder={t('login.username')}
                      size="large"
                    />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[{ required: true, message: t('login.pleaseInputPassword') }]}
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder={t('login.password')}
                      size="large"
                    />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={loading}
                      block
                      size="large"
                    >
                      {t('login.title')}
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'register',
              label: t('login.register'),
              children: (
                <Form onFinish={onRegister} layout="vertical">
                  <Form.Item
                    name="username"
                    rules={[{ required: true, message: t('login.pleaseInputUsername') }]}
                  >
                    <Input
                      prefix={<UserOutlined />}
                      placeholder={t('login.username')}
                      size="large"
                    />
                  </Form.Item>
                  <Form.Item
                    name="email"
                    rules={[
                      { type: 'email', message: t('login.pleaseInputValidEmail') },
                    ]}
                  >
                    <Input
                      prefix={<MailOutlined />}
                      placeholder={t('login.emailOptional')}
                      size="large"
                    />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[
                      { required: true, message: t('login.pleaseInputPassword') },
                      { min: 6, message: t('login.passwordMinLength') },
                    ]}
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder={t('login.password')}
                      size="large"
                    />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={loading}
                      block
                      size="large"
                    >
                      {t('login.register')}
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default Login;



