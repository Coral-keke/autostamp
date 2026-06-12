# 🔖 Auto-Stamp System 自动盖章系统

PDF / DWG 文件自动盖章服务，支持**外部系统异步调用**和 **Web UI 拖拽**两种模式。

## 📡 API 架构

```
外部系统 (VP/DWF/...)                 Auto-Stamp                 Web UI
     │                                    │                        │
     │  POST /api/v1/stamp/submit         │                        │
     │  {requestNo, fileUrl, sealCode,    │                        │
     │   position, callbackUrl}            │                        │
     │ ─────────────────────────────────→ │                        │
     │                                    │  ACCEPTED              │
     │ ←───────────────────────────────── │                        │
     │                                    │                        │
     │                                    │  [后台处理]              │
     │                                    │  1. 下载文件             │
     │                                    │  2. 盖章                │
     │                                    │  3. 回调通知             │
     │                                    │                        │
     │  回调 POST callbackUrl             │                        │
     │  {status: SUCCESS, fileUrl}        │                        │
     │ ←───────────────────────────────── │                        │
     │                                    │                        │
     │  GET /api/v1/stamp/download/{no}   │                        │
     │ ─────────────────────────────────→ │                        │
     │ ←──── stamped.pdf ─────────────── │                        │
```

## 🔌 API 接口

### 外部系统调用（异步）

```bash
# 提交盖章请求
curl -X POST http://localhost:8000/api/v1/stamp/submit \
  -H "Content-Type: application/json" \
  -d '{
    "requestNo": "VP202606040001",
    "businessId": "VP-BIZ-20260604-0001",
    "systemCode": "VP",
    "systemName": "VP系统",
    "contractName": "采购合同-测试.pdf",
    "fileUrl": "https://example.com/contracts/doc.pdf",
    "fileType": "pdf",
    "sealType": "OFFICIAL",
    "sealCode": "VP_GZ_001",
    "sealReason": "审批通过，发起自动盖章",
    "pageNo": 1,
    "position": {"x": 420, "y": 680, "width": 120, "height": 120},
    "operator": {"userId": "zhangsan", "userName": "张三"},
    "callbackUrl": "https://example.com/api/seal/callback",
    "remark": "测试"
  }'

# 查询状态
curl http://localhost:8000/api/v1/stamp/status/VP202606040001

# 下载结果
curl -O http://localhost:8000/api/v1/stamp/download/VP202606040001
```

### 回调格式

```json
{
  "requestNo": "VP202606040001",
  "businessId": "VP-BIZ-20260604-0001",
  "status": "SUCCESS",
  "fileUrl": "http://localhost:8000/api/v1/stamp/download/VP202606040001",
  "fileType": "pdf",
  "stampedFileName": "stamped_采购合同-测试.pdf"
}
```

### 印章管理

```bash
# 上传印章
curl -X POST http://localhost:8000/api/v1/seals \
  -F "name=VP公章" \
  -F "seal_code=VP_GZ_001" \
  -F "seal_type=OFFICIAL" \
  -F "file=@seal.png" \
  -F "default_width_mm=40" \
  -F "default_height_mm=40"

# 按编码查询
curl http://localhost:8000/api/v1/seals/code/VP_GZ_001

# 列表
curl http://localhost:8000/api/v1/seals?seal_type=OFFICIAL
```

## 🏗️ 项目结构

```
auto-stamp/                      26 files
├── backend/
│   ├── api/
│   │   ├── seals.py          印章 CRUD + sealCode 查询
│   │   └── stamp.py          异步提交 / 状态查询 / 下载 / 同步模式
│   ├── engines/
│   │   ├── pdf_engine.py     PyMuPDF 盖章（支持独立宽高）
│   │   ├── converter.py      ODA CLI: DWG↔PDF↔DWF
│   │   └── dwf_engine.py     占位（待 ODA SDK 直出）
│   ├── models/
│   │   ├── seal.py           印章模型（sealCode + sealType）
│   │   └── request.py        请求/响应/回调模型
│   ├── main.py               FastAPI 入口
│   └── config.py             配置（下载/回调/坐标）
├── frontend/                  Vue 3 + Fabric.js 拖拽盖章
└── docker-compose.yml
```

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STAMP_BASE_URL` | `http://localhost:8000` | 回调中返回的下载地址前缀 |
| `STAMP_DOWNLOAD_TIMEOUT` | 60 | 文件下载超时(秒) |
| `STAMP_CALLBACK_TIMEOUT` | 30 | 回调超时(秒) |
| `STAMP_CALLBACK_RETRY_COUNT` | 3 | 回调重试次数 |

## 🚀 启动

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install && npm run dev

# Docker
docker compose up -d
```

## 🔧 前置依赖

- Python 3.11+ / PyMuPDF / httpx
- ODA File Converter (DWG→DWF)
- Node.js 18+ (前端)
