# chinacnu 期货（自主交易系统骨架）

> 基于 RQData + 外部交易API 的“研究→信号→风控→执行”闭环骨架。

## 目标
- 覆盖股票/期货多市场数据接入（含国内主流交易所）
- 支持接入真实行情/下单API（服务端代理，前端不暴露token）
- 核心策略：热卷（HC）+ 燃油（FU）

## 目录
- `app/main.py`：FastAPI 控制层（含 realtime/kline/order API 代理）
- `data/rq_client.py`：RQData 数据客户端
- `strategies/hc_fu_trend.py`：HC/FU 策略
- `engine/paper_executor.py`：模拟执行与风控
- `config/settings.example.yaml`：配置模板

## 快速开始
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/settings.example.yaml config/settings.yaml
# 填写 trading_api.base_url/token 以及接口路径
uvicorn app.main:app --reload --port 8099
```

## 实时接口（本地后端）
- `GET /api/market/realtime?symbol=HC`
- `GET /api/market/kline?symbol=HC&period=1m&limit=120`
- `POST /api/order`（symbol/side/offset/qty）

## 注意
- 当前默认 `paper` 模式；实盘请先完成风控审批与小资金联调。
- 你发过一次明文token，建议接入后立即轮换。
