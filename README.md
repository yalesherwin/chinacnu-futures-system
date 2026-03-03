# chinacnu 期货（自主交易系统骨架）

> 基于 RQData 文档能力的“研究→信号→风控→执行”闭环骨架。

## 目标
- 覆盖股票/期货多市场数据接入（含国内主流交易所）
- 先跑模拟盘（paper trading），再接实盘执行接口
- 核心策略：热卷（HC）+ 燃油（FU）

## 目录
- `app/main.py`：FastAPI 控制层
- `data/rq_client.py`：RQData 数据客户端
- `strategies/hc_fu_trend.py`：HC/FU 策略
- `engine/paper_executor.py`：模拟执行与风控
- `config/settings.example.yaml`：配置模板

## 快速开始
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/settings.example.yaml config/settings.yaml
# 填写 rqdata 账号密码
uvicorn app.main:app --reload --port 8099
```

## 注意
- 当前为系统骨架与模拟盘流程，不直接代客实盘下单。
- 实盘前需接入合规券商/期货通道，并完成风控审批。
