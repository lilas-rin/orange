# XX脐橙产销数据分析与智能决策平台

前后端分离的脐橙产业大数据分析与决策支持系统。后端使用 **Python + FastAPI + SQLAlchemy + MySQL**，前端使用 **Vue3 + Vite + TypeScript + Element Plus + ECharts**。

## 目录结构

```
D:/orange/
├── backend/        # Python 后端
│   ├── app/        # 业务代码
│   │   ├── api/    # API 路由
│   │   ├── core/   # 配置 / 安全 / 日志 / 异常
│   │   ├── db/     # 数据库连接 / 基类
│   │   ├── ml/     # 机器学习模型
│   │   ├── models/ # SQLAlchemy ORM 模型（18 张表）
│   │   ├── schemas/# Pydantic 校验
│   │   ├── services/# 业务逻辑 / 大屏 / 分析 / 决策引擎
│   │   └── main.py # 应用入口
│   ├── migrations/ # Alembic 数据库迁移
│   ├── scripts/    # init_db / seed
│   └── requirements.txt
├── frontend/       # Vue3 前端
│   ├── src/
│   │   ├── api/    # 接口封装
│   │   ├── views/  # 页面
│   │   ├── components/
│   │   ├── layouts/
│   │   └── router/
│   └── package.json
└── README.md
```

## 技术栈

- **后端**：FastAPI、SQLAlchemy 2.0、Alembic、Pydantic、PyMySQL、scikit-learn、joblib
- **前端**：Vue 3、Vite、TypeScript、Element Plus、Pinia、Vue Router、ECharts、Axios、dayjs
- **数据库**：MySQL 8.0+

## 环境要求

- Python 3.13（本项目使用隔离虚拟环境）
- Node.js 22+
- MySQL 8.0+（数据库由 `scripts.init_db` 自动创建）

## 快速启动

### 1. 后端

```bash
cd backend

# 创建虚拟环境并安装依赖（已初始化可跳过）
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# 创建数据库并执行迁移
.venv/Scripts/python.exe -m scripts.init_db

# 生成演示数据并训练模型
.venv/Scripts/python.exe -m scripts.seed

# 启动服务
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

后端 API 文档：`http://127.0.0.1:8000/docs`

### 2. 前端

```bash
cd frontend

# 安装依赖（已初始化可跳过）
npm install

# 开发服务器
npm run dev
```

前端地址：`http://127.0.0.1:5173`

生产构建：

```bash
npm run build
```

## 默认账号

| 账号       | 密码          | 角色  | 权限说明     |
| -------- | ----------- | --- | -------- |
| admin    | admin123    | 管理员 | 全部权限     |
| operator | operator123 | 操作员 | 数据/模型/分析 |

## 主要功能

- **后台管理系统**：登录认证（JWT）、区域/产地/品种管理、产量/销量/价格/市场/病虫害 CRUD、Excel/CSV 数据导入、数据分析、模型训练与预测、用户/角色/日志。
- **数字大屏**:
  - 以全国市场地图为视觉主体，自适应 1920×1080 缩放
  - 省份名称大字号标注、流向线双层高亮 + 箭头动效
  - 赣州市 18 县区产量/均价/风险钻取
  - 县区联动：产销趋势、价格预测、病虫害风险
  - 产地详情：五维雷达 + 价格预测
  - 底部核心指标卡片 / 赣州县区快捷切换
  - 智能决策建议

## 大屏交互与导航

平台默认首页为数字大屏，按以下层级进入后台管理：

1. 打开应用后首先进入**全国市场**大屏。
2. 点击地图上的**江西省**（或顶部"赣州产区"按钮）下钻到**赣州市 18 县区**视图。
3. 点击**信丰县**区域即可进入**后台管理系统**；未登录时会先到登录页，登录成功后自动进入后台。
4. 其他县区点击后打开产销联动详情抽屉。

## 地图数据说明

大屏使用的中国及赣州市 GeoJSON 边界数据来自 [阿里云 DataV GeoAtlas](https://geo.datav.aliyun.com/)，该数据基于国家标准行政区划边界，包含台湾省、香港、澳门及南海诸岛。地图仅用于内部数据可视化展示。

## 机器学习模型

- **价格预测**：RandomForest 回归，输出未来 6 个月均价及置信区间。
- **病虫害风险预测**：RandomForest 三分类（低/中/高），输出未来 3 个月县区风险等级。

模型训练结果与预测结果均持久化到数据库，便于大屏与决策引擎调用。

## 数据口径

平台 KPI 与地图按「产季年」口径汇总：产季年从当年 11 月—次年 10 月，以匹配脐橙 11 月集中采收、销售跨年的产业规律，避免自然年口径下产销率失真。

## 环境变量配置

复制模板并按自己的环境修改：

```bash
cd backend
cp .env.example .env
```

`.env` 中的关键项：

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | MySQL 连接串，格式 `mysql+pymysql://用户名:密码@主机:端口/库名?charset=utf8mb4` |
| `SECRET_KEY` | JWT 签名密钥，生产环境务必换成随机长字符串 |
| `CORS_ORIGINS` | 允许跨域的前端地址 |

> `.env` 已被 `.gitignore` 排除，**不要提交到仓库**。

生成随机密钥：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

修改 `DATABASE_URL` 后重新执行 `python -m scripts.init_db` 与 `python -m scripts.seed`。
