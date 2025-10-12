import requests
import json

url = "http://127.0.0.1:8000/api/research/start/stream"
payload = {
    "topic": "今天的日期，你是谁",
    "locale": "zh-CN"
}

# stream=True 是关键：允许逐块接收响应（即 SSE 流）
with requests.post(url, json=payload, stream=True) as response:
    print("Status:", response.status_code)
    print("Headers:", response.headers)
    print("\n--- Start Receiving SSE ---\n")

    # 一行一行地迭代输出
    for line in response.iter_lines(decode_unicode=True):
        if line:  # 跳过空行
            if line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                try:
                    data = json.loads(data_str)
                    print(f"Event Data: {json.dumps(data, ensure_ascii=False, indent=2)}")
                except json.JSONDecodeError:
                    print(f"Raw Data: {data_str}")
            else:
                print(line)
