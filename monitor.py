import requests
import json
import os

# 환경 변수 (GitHub Secrets에서 불러옴)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
URL = "https://scd.dgplatform.net/wmr-owg2026/competition/api/ENG/medallists"

# kini 님의 검증된 마스터 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://mediazone.milanocortina2026.org/",
    "Origin": "https://mediazone.milanocortina2026.org",
    "Cookie": "D+sZWRW3OzoNWJngrvxAa1hbQ8ymY3ykhexqobIaI1M="
}

def send_telegram(message):
    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(send_url, data=payload)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def monitor():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return

    athletes = data.get('athletes', [])
    if not athletes:
        return

    # 이전 상태 로드
    state_file = 'last_state.json'
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            prev = json.load(f)
    else:
        # 초기값이 없을 경우 현재 시점 데이터로 생성
        prev = {"max_gold": 0, "klaebo_gold": 0, "top_names": []}

    # 현재 상태 분석
    current_max_gold = max(a['medalsGold'] for a in athletes)
    current_top_names = sorted([a['fullName'] for a in athletes if a['medalsGold'] == current_max_gold])
    
    klaebo = next((a for a in athletes if "KLAEBO" in a['fullName']), None)
    current_klaebo_gold = klaebo['medalsGold'] if klaebo else 0

    alerts = []

    # 로직 1: 최다 금메달리스트 변동 감지
    if current_max_gold > prev['max_gold'] or current_top_names != prev.get('top_names', []):
        names_str = ", ".join(current_top_names)
        alerts.append(f"🥇 [최다 금메달 업데이트]\n개수: {current_max_gold}개\n명단: {names_str}")

    # 로직 2: KLAEBO 금메달 추가 감지
    if current_klaebo_gold > prev['klaebo_gold']:
        alerts.append(f"🎿 [KLAEBO 금메달 소식]\n클레보 선수가 금메달을 추가했습니다!\n현재 총 {current_klaebo_gold}개")

    # 알림 전송 및 상태 저장
    if alerts:
        send_telegram("\n\n".join(alerts))
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump({
                "max_gold": current_max_gold, 
                "klaebo_gold": current_klaebo_gold,
                "top_names": current_top_names
            }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    monitor()
