# Zen Metadata Frontend

React + TypeScript + Ant Design 前端应用

## 技术栈

- React 19
- TypeScript
- Ant Design 5.x
- React Router v6
- Zustand (状态管理)
- Axios (HTTP 客户端)
- React Flow (图可视化)
- ECharts (图表)

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 环境变量

创建 `.env` 文件：

```
VITE_API_BASE_URL=http://localhost:8000
```

## 项目结构

```
src/
├── components/      # 通用组件
│   └── Layout/     # 布局组件
├── pages/          # 页面组件
│   ├── Dashboard/  # 仪表板
│   ├── GraphView/  # 图可视化
│   ├── EntityBrowser/ # 实体浏览器
│   ├── Collection/ # 采集管理
│   └── Analytics/  # 统计分析
├── services/       # API 服务
├── store/          # 状态管理
├── types/          # TypeScript 类型定义
└── App.tsx         # 主应用组件
```
