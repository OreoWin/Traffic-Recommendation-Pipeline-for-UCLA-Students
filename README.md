# Traffic-Recommendation-Pipeline-for-UCLA-Students

data pipeline powered by external APIs and LLMs

---

This project provides real-time travel recommendations for UCLA students by analyzing current traffic conditions from Westwood to popular LA destinations.

The pipeline integrates:

- TomTom Routing API for real-time traffic and travel time data

- Groq + Llama 3 for natural-language recommendation generation

- A modular Python architecture that simulates a daily-style report system

The full workflow:  raw API data → structured metrics → ranking logic → AI-generated insights

---

## Pipeline Structure
```text
User Input (Fixed Origin: UCLA)
↓
TomTom Routing API
↓
Travel metrics calculation
(congestion index, travel time, delay)
↓
Route scoring & ranking
(best + second-best destination)
↓
LLM recommendation generation (Groq)
↓
Daily-style report rendering
```

系统从 TomTom API 获取 Westwood 到洛杉矶多个目的地的实时路况信息，通过自定义评分逻辑筛选出最推荐去处，再利用 LLM（Groq + Llama 3）生成自然语言推荐文案，最终形成日报式输出。

该项目完整覆盖从数据采集 → 处理 → 分析 → AI生成 → 输出的全过程。

# 核心能力展示

- 外部 API 调用与数据接入

- 路况数据解析与指标提取

- 评分逻辑设计与推荐算法

- LLM 语义生成与 prompt 工程

- 模块化 Python 管道设计

- 可扩展自动化结构

## Next Step 
- 接入调度系统（GitHub Actions / Prefect）

- 输出为 Web Dashboard 或地图可视化

- 增加更多目的地或用户偏好选项
