import requests
import json
import os

# GitHub Secrets에서 환경 변수 로드
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# API 엔드포인트
ATHLETES_URL = "https://scd.dgplatform.net/wmr-owg2026/competition/api/ENG/medallists"
MEDALS_URL = "https://scd.dgplatform.net/wmr-owg2026/competition/api/ENG/medals"

# kini 님의 마스터 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://mediazone.milanocortina2026.org/",
    "Origin": "https://mediazone.milanocortina2026.org",
    "Cookie": "D+sZWRW3OzoNWJngrvxAa1hbQ8ymY3ykhexqobIaI1M="
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def format_medal_table(title, medal_data):
    table = f"📊 *{title}*\n"
    table += "`NOC | 금 | 은 | 동 | 합계`\n"
    table += "---------------------------\n"
    for i, m in enumerate(medal_data[:5]):
        table += f"{i+1}. {m['organisation']} | {m['gold']} | {m['silver']} | {m['bronze']} | {m['total']}\n"
    return table

def monitor():
    try:
        # 데이터 수집
        res_athletes = requests.get(ATHLETES_URL, headers=HEADERS, timeout=30)
        res_medals = requests.get(MEDALS_URL, headers=HEADERS, timeout=30)
        
        data_athletes = res_athletes.json()
        data_medals = res_medals.json()
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return

    # --- 1. 국가별 순위 분석 ---
    medal_list = data_medals.get('medals', [])
    # 금메달순 정렬 (금 > 은 > 동)
    sort_gold = sorted(medal_list, key=lambda x: (-x['gold'], -x['silver'], -x['bronze']))
    # 합계순 정렬 (합계 > 금)
    sort_total = sorted(medal_list, key=lambda x: (-x['total'], -x['gold']))

    # --- 2. 선수별 기록 분석 ---
    athletes = data_athletes.get('athletes', [])
    current_max_gold = max(a['medalsGold'] for a in athletes) if athletes else 0
    current_top_names = sorted([a['fullName'] for a in athletes if a['medalsGold'] == current_max_gold])
    
    klaebo = next((a for a in athletes if "KLAEBO" in a['fullName']), None)
    current_klaebo_gold = klaebo['medalsGold'] if klaebo else 0

    # --- 3. 메시지 구성 ---
    report = []
    
    # [국가 순위 섹션]
    report.append(format_medal_table("금메달 순위 (TOP 5)", sort_gold))
    report.append(format_medal_table("합계 순위 (TOP 5)", sort_total))
    
    # [선수 기록 섹션]
    athlete_msg = "👤 *선수 기록 업데이트*\n"
    athlete_msg += f"🥇 최다 금메달: {current_max_gold}개\n({', '.join(current_top_names)})\n"
    athlete_msg += f"🎿 클레보(KLAEBO): 금 {current_klaebo_gold}개"
    report.append(athlete_msg)

    # 텔레그램 전송
    send_telegram("\n\n".join(report))

    # --- 4. 상태 업데이트 (last_state.json 기록용) ---
    with open('last_state.json', 'w', encoding='utf-8') as f:
        json.dump({
            "max_gold": current_max_gold,
            "klaebo_gold": current_klaebo_gold,
            "top_names": current_top_names
        }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    monitor()
