import requests

API_KEY = "1sbmG*******aWD5dBk6"

# UCLA (Westwood) 坐标
origin = "34.04,-118.26"

# Santa Monica 坐标
destination = "34.0195,-118.4912"

url = f"https://api.tomtom.com/routing/1/calculateRoute/{origin}:{destination}/json"

params = {
    "key": API_KEY,
    "traffic": "true"
}

response = requests.get(url, params=params)

data = response.json()

summary = data["routes"][0]["summary"]
travel_time = summary["travelTimeInSeconds"]
delay = summary.get("trafficDelayInSeconds", 0)

free_flow_time = travel_time - delay

print("从 UCLA 到 Santa Monica：")
print(f"当前行车时间: {travel_time/60:.2f} 分钟")
print(f"无拥堵时间: {free_flow_time/60:.2f} 分钟")

congestion_ratio = travel_time / free_flow_time
print(f"拥堵指数: {congestion_ratio:.2f}")

