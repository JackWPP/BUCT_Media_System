# 视觉北化 - 前端

基于 Vue 3 + TypeScript + Vite + Naive UI 的现代化前端应用。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript 超集
- **Vite** - 下一代前端构建工具
- **Naive UI** - Vue 3 组件库
- **Pinia** - Vue 3 状态管理
- **Vue Router** - 官方路由管理器
- **Axios** - HTTP 请求库
- **VueUse** - Vue Composition API 工具集

## 项目结构

```
src/
├── api/                 # API 请求封装
│   ├── index.ts        # Axios 实例配置
│   ├── auth.ts         # 认证相关 API
│   └── photo.ts        # 照片相关 API
├── assets/             # 静态资源
├── components/         # 可复用组件
│   ├── common/         # 通用组件
│   ├── photo/          # 照片相关组件
│   └── layout/         # 布局组件
├── router/             # 路由配置
├── stores/             # 状态管理
│   ├── auth.ts         # 认证状态
│   ├── photo.ts        # 照片状态
│   └── app.ts          # 应用状态
├── types/              # TypeScript 类型定义
├── utils/              # 工具函数
├── views/              # 页面视图
│   ├── Login.vue       # 登录页
│   ├── Gallery.vue     # 照片画廊
│   ├── Upload.vue      # 上传页面
│   └── NotFound.vue    # 404 页面
├── App.vue             # 根组件
└── main.ts             # 应用入口
```

## 开发指南

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173

### 生产构建

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 环境变量

在项目根目录创建 `.env.development` 和 `.env.production` 文件：

### .env.development
```
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=视觉北化 - Dev
```

### .env.production
```
VITE_API_BASE_URL=/api
VITE_APP_TITLE=视觉北化
```

## 功能特性

### 已实现
- ✅ 用户认证（登录/登出）
- ✅ 照片列表展示
- ✅ 照片筛选（季节、类别、状态）
- ✅ 照片搜索（防抖处理）
- ✅ 分页功能
- ✅ 照片详情模态框
- ✅ 照片编辑（描述、分类、季节）
- ✅ 照片删除（二次确认）
- ✅ 照片上传（单张/批量）
- ✅ 拖拽上传
- ✅ 上传进度显示
- ✅ 骨架屏加载动画
- ✅ 空状态提示
- ✅ 响应式布局
- ✅ 全局样式优化

### 待实现
- 🚧 标签管理（添加/删除标签）
- 🚧 图片懒加载
- 🚧 虚拟滚动（可选）
- 🚧 暗色模式完善

## 开发规范

### 代码风格
- 使用 TypeScript 进行类型检查
- 使用 Vue 3 Composition API (Script Setup)
- 遵循 ESLint 规则

### 提交规范
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具相关

## 默认测试账号

- 邮箱: `admin@buct.edu.cn`
- 密码: `admin123`

## 注意事项

1. 确保后端服务已启动（默认端口 8000）
2. 首次登录需要后端数据库中有管理员账号
3. 上传功能需要配置正确的文件存储路径

## 相关链接

- [Vue 3 文档](https://vuejs.org/)
- [Vite 文档](https://vitejs.dev/)
- [Naive UI 文档](https://www.naiveui.com/)
- [Pinia 文档](https://pinia.vuejs.org/)
- [Vue Router 文档](https://router.vuejs.org/)

## 许可证

MIT
