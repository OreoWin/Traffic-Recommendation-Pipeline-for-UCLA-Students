import os
import requests
import json
from datetime import datetime
from groq import Groq

# ============ setup ============

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "1sb*****jaWD5dBk6")
GROQ_API_KEY = os.getenv("GROQ_API_KEY","gsk_9ZUZCjyjpllna1JXCTTTWG*****1kpmZD8oFTvYAhdAt")

# fixed origin - UCLA
ORIGIN_NAME = "Westwood (UCLA)"
ORIGIN_COORD = "34.04,-118.26"

# destination (keep updating)
DESTINATIONS = [
    {"name": "Santa Monica Pier",      "coord": "34.0094,-118.4973"},
    {"name": "Griffith Observatory",   "coord": "34.1184,-118.3004"},
    {"name": "The Grove",              "coord": "34.0729,-118.3574"},
    {"name": "LACMA",                  "coord": "34.0638,-118.3592"},
]

# LLM client
client = Groq(api_key=GROQ_API_KEY)


# ============ core funcs ============

def get_route_metrics(origin_coord, dest_coord, api_key):
    """
    调用 TomTom Routing API 返回一个 dict
    {
        'travel_time_min': 当前路况下的行车时间（分钟）,
        'free_flow_time_min': 无拥堵时间（分钟）,
        'congestion_ratio': 拥堵指数（travel_time / free_flow）
    }
    """
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{origin_coord}:{dest_coord}/json"
    params = {
        "key": api_key,
        "traffic": "true",
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    summary = data["routes"][0]["summary"]
    travel_time = summary["travelTimeInSeconds"]
    delay = summary.get("trafficDelayInSeconds", 0)
    free_flow_time = travel_time - delay

    travel_time_min = travel_time / 60
    free_flow_time_min = free_flow_time / 60 if free_flow_time > 0 else travel_time_min
    congestion_ratio = travel_time / free_flow_time if free_flow_time > 0 else 1.0

    return {
        "travel_time_min": travel_time_min,
        "free_flow_time_min": free_flow_time_min,
        "congestion_ratio": congestion_ratio,
    }


def build_route_record(origin_name, origin_coord, dest_name, dest_coord):
    """
    从 origin -> dest 生成一条完整记录
    """
    metrics = get_route_metrics(origin_coord, dest_coord, TOMTOM_API_KEY)
    record = {
        "origin_name": origin_name,
        "origin_coord": origin_coord,
        "dest_name": dest_name,
        "dest_coord": dest_coord,
        **metrics,
    }
    return record


def generate_basic_text_summary(record, rank_label=None):
    """
    info abstract,rank_label(best/second best)
    """
    ratio = record["congestion_ratio"]
    if ratio < 1.2:
        status = "Nice!"
    elif ratio < 1.5:
        status = "Yikes"
    else:
        status = "Oh noooo"

    tag = f"" if rank_label else ""
    text = (
        f"{tag} From {record['origin_name']} to {record['dest_name']}：\n"
        f"- Estimated travel time now: {record['travel_time_min']:.1f} min\n"
        f"- Free flow travel time: {record['free_flow_time_min']:.1f} min\n"
        f"- Traffic congestion index: {ratio:.2f}（{status}）\n"
    )
    return text


def generate_llm_recommendation(route_record):
    """
    使用 Groq + Llama3 生成出行建议（针对单一目的地）
    """
    route_json_str = json.dumps(route_record, ensure_ascii=False, indent=2)

    prompt = f"""
    你是一个懂洛杉矶路况的出行助手，主要服务 UCLA 学生。

    下面是从 {route_record['origin_name']} 到 {route_record['dest_name']} 的实时路况数据：

    {route_json_str}

    请根据这些数据完成以下任务：
    1. 判断现在出发去 {route_record['dest_name']} 是否合适，用“推荐 / 一般 / 不推荐”给出结论，并说明原因。
    2. 用非常口语化的方式写成 3-5 句话，语气轻松，目标用户是 UCLA 在读学生。
    3. 如果拥堵指数大于 1.5，请提醒“建议避开当前时段，考虑晚一点再出发”。

    输出时不要重复 JSON 数据，只给最终文案；用中文回答。
    """

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=1.2,
    )

    return (completion.choices[0].message.content or "").strip()


def score_route(record):
    """
    给每个目的地一个综合评分，越小越好
    - 优先考虑不堵（congestion_ratio 小）
    - 其次考虑行车时间短（travel_time_min 小）

    打分方式：score = travel_time_min * congestion_ratio
    """
    travel = record["travel_time_min"]
    ratio = record["congestion_ratio"]
    return travel * ratio


def pick_top_destinations(records, top_k=2):
    """
    从所有目的地里选出：最推荐 & 第二推荐
    逻辑：
    1. 先过滤掉特别堵的（拥堵指数 >= 1.5 的视为“较堵”）
    2. 如果剩下的 >= top_k，就在这些里面按 score 排序取前 top_k
    3. 如果剩下的 < top_k，就退一步：在全体 records 里按 score 排序取前 top_k
    """
    not_too_congested = [r for r in records if r["congestion_ratio"] < 1.5]

    candidate_pool = (
        not_too_congested if len(not_too_congested) >= top_k else records
    )

    sorted_records = sorted(candidate_pool, key=score_route)
    return sorted_records[:top_k]


def render_report(best_records_with_reco):
    """
    best_records_with_reco: list[{"record": ..., "llm_reco": "..."}]
    只渲染：最推荐 + 第二推荐
    """
    today = datetime.now().strftime("%Y-%m-%d")
    header = f"Where to go for UCLA students 出行指南（{today}）\n====================\n\n"

    labels = ["best", "second_best"]

    blocks = []
    for idx, item in enumerate(best_records_with_reco):
        record = item["record"]
        llm_reco = item["llm_reco"]
        label = labels[idx] if idx < len(labels) else None

        route_summary = generate_basic_text_summary(record, rank_label=label)
        rec_block = "<Rebecca's recommendation>\n" + (llm_reco if llm_reco else "<sry...Rebecca is offline>") + "\n"
        blocks.append(route_summary + "\n" + rec_block)

    body = "\n".join(blocks)
    return header + body


# ============ main ============

def main():
    # 1. 对所有destination算路况
    all_records = []
    for dest in DESTINATIONS:
        record = build_route_record(
            ORIGIN_NAME,
            ORIGIN_COORD,
            dest["name"],
            dest["coord"],
        )
        all_records.append(record)

    # 2. 选best & second_best
    top_records = pick_top_destinations(all_records, top_k=2)

    # 3. LLM
    best_records_with_reco = []
    for record in top_records:
        llm_reco = generate_llm_recommendation(record)
        best_records_with_reco.append({
            "record": record,
            "llm_reco": llm_reco,
        })

    # 4. render
    report_text = render_report(best_records_with_reco)
    print(report_text)


if __name__ == "__main__":
    main()
