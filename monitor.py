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
    if not medal_data:
        return f"📊 *{title}*\n데이터를 불러올 수 없습니다."
    
    table = f"📊 *{title}*\n"
    table += "`NOC | 금 | 은 | 동 | 합계`\n"
    table += "---------------------------\n"
    for i, m in enumerate(medal_data[:5]):
        # medalsNumber에서 'Total' 타입을 찾아 데이터 추출
        total_data = next((item for item in m.get('medalsNumber', []) if item['type'] == 'Total'), {})
        noc = m.get('organisation', 'N/A')
        gold = total_data.get('gold', 0)
        silver = total_data.get('silver', 0)
        bronze = total_data.get('bronze', 0)
        total = total_data.get('total', 0)
        
        table += f"{i+1}. {noc} | {gold} | {silver} | {bronze} | {total}\n"
    return table

def monitor():
    try:
        res_athletes = requests.get(ATHLETES_URL, headers=HEADERS, timeout=30)
        res_medals = requests.get(MEDALS_URL, headers=HEADERS, timeout=30)
        
        data_athletes = res_athletes.json()
        data_medals = res_medals.json()
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return

    # --- 1. 국가별 순위 분석 (구조에 맞게 수정) ---
    # 제공해주신 JSON 구조: data_medals['medalStandings']['medalsTable']
    medal_list = data_medals.get('medalStandings', {}).get('medalsTable', [])

    def get_total_stats(entry):
        total_info = next((item for item in entry.get('medalsNumber', []) if item['type'] == 'Total'), {})
        return {
            'gold': total_info.get('gold', 0),
            'silver': total_info.get('silver', 0),
            'bronze': total_info.get('bronze', 0),
            'total': total_info.get('total', 0)
        }

    # 정렬을 위해 각 국가 데이터에 total_stats 매핑
    processed_medals = []
    for m in medal_list:
        stats = get_total_stats(m)
        m.update(stats) # 정렬 편의를 위해 필드 주입
        processed_medals.append(m)

    # 금메달순 정렬 (금 > 은 > 동)
    sort_gold = sorted(processed_medals, key=lambda x: (-x['gold'], -x['silver'], -x['bronze']))
    # 합계순 정렬 (합계 > 금)
    sort_total = sorted(processed_medals, key=lambda x: (-x['total'], -x['gold']))

    # --- 2. 선수별 기록 분석 ---
    athletes = data_athletes.get('athletes', [])
    current_max_gold = max(a['medalsGold'] for a in athletes) if athletes else 0
    current_top_names = sorted([a['fullName'] for a in athletes if a['medalsGold'] == current_max_gold])
    
    klaebo = next((a for a in athletes if "KLAEBO" in a['fullName']), None)
    current_klaebo_gold = klaebo['medalsGold'] if klaebo else 0

    # --- 3. 메시지 구성 ---
    report = []
    report.append(format_medal_table("금메달 순위 (TOP 5)", sort_gold))
    report.append(format_medal_table("합계 순위 (TOP 5)", sort_total))
    
    athlete_msg = "👤 *선수 기록 업데이트*\n"
    athlete_msg += f"🥇 최다 금메달: {current_max_gold}개\n({', '.join(current_top_names)})\n"
    athlete_msg += f"🎿 클레보(KLAEBO): 금 {current_klaebo_gold}개"
    report.append(athlete_msg)

    # 텔레그램 전송
    send_telegram("\n\n".join(report))

    # --- 4. 상태 업데이트 ---
    with open('last_state.json', 'w', encoding='utf-8') as f:
        json.dump({
            "max_gold": current_max_gold,
            "klaebo_gold": current_klaebo_gold,
            "top_names": current_top_names
        }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    monitor()
