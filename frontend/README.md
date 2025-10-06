# Deep Research 前端应用

基于React + TypeScript + Tailwind CSS构建的现代化前端界面，为AI深度研究系统提供用户交互界面。

## 特性

- 🎨 **现代化UI设计** - 温和、专业的视觉风格
- 📱 **响应式布局** - 适配各种设备尺寸
- 🔄 **状态管理** - 使用React Context管理研究状态
- 📊 **流程可视化** - 实时显示研究进度和结果
- 📄 **报告导出** - 支持Markdown格式导出
- 🚀 **流畅动画** - 使用Framer Motion实现平滑过渡

## 页面结构

- **首页 (/)** - 研究主题输入
- **研究计划 (/plan)** - 展示和编辑研究计划
- **研究进度 (/progress)** - 实时显示研究执行过程
- **研究报告 (/report)** - 展示最终研究成果

## 安装和运行

```bash
# 安装依赖
npm install

# 启动开发服务器
npm start

# 构建生产版本
npm run build
```

## 技术栈

- React 18
- TypeScript
- Tailwind CSS
- React Router v6
- Framer Motion
- Lucide React (图标)

## 开发说明

前端应用采用前后端分离架构，通过API与后端langgraph服务进行通信。当前版本为演示版本，包含模拟数据和交互逻辑。