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

def format_medal_table(title, sorted_list):
    """TOP 5와 KOR, JPN을 순위순으로 포함한 테이블 생성"""
    if not sorted_list:
        return f"📊 *{title}*\n데이터를 불러올 수 없습니다."
    
    table = f"📊 *{title}*\n"
    table += "`순위. NOC | 금 | 은 | 동 | 합계`\n"
    table += "---------------------------\n"
    
    # 1. TOP 5 출력
    top5 = sorted_list[:5]
    for i, m in enumerate(top5):
        table += f"{i+1}. {m['organisation']} | {m['gold']} | {m['silver']} | {m['bronze']} | {m['total']}\n"
    
    # 2. KOR, JPN 추출 및 순위순 정렬
    target_codes = ['KOR', 'JPN']
    top5_codes = [m['organisation'] for m in top5]
    
    # TOP 5에 없는 대상 국가들을 찾아 현재 순위와 함께 리스트화
    extra_targets = []
    for idx, m in enumerate(sorted_list):
        if m['organisation'] in target_codes and m['organisation'] not in top5_codes:
            extra_targets.append((idx + 1, m))
    
    # 대상 국가들끼리도 순위(idx)에 따라 정렬 (순위가 높은 나라가 먼저 오도록)
    extra_targets.sort(key=lambda x: x[0])
    
    if extra_targets:
        table += "...\n"
        for rank, m in extra_targets:
            table += f"{rank}. {m['organisation']} | {m['gold']} | {m['silver']} | {m['bronze']} | {m['total']}\n"
        
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

    # --- 1. 국가별 순위 데이터 파싱 ---
    medal_table = data_medals.get('medalStandings', {}).get('medalsTable', [])
    processed_medals = []
    
    for entry in medal_table:
        total_info = next((item for item in entry.get('medalsNumber', []) if item['type'] == 'Total'), {})
        processed_medals.append({
            'organisation': entry.get('organisation'),
            'gold': total_info.get('gold', 0),
            'silver': total_info.get('silver', 0),
            'bronze': total_info.get('bronze', 0),
            'total': total_info.get('total', 0)
        })

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

    # --- 3. 리포트 생성 ---
    report = []
    report.append(format_medal_table("금메달 순위 (TOP 5 + α)", sort_gold))
    report.append(format_medal_table("합계 순위 (TOP 5 + α)", sort_total))
    
    athlete_msg = "👤 *선수 기록 업데이트*\n"
    athlete_msg += f"🥇 최다 금메달: {current_max_gold}개\n({', '.join(current_top_names)})\n"
    athlete_msg += f"🎿 클레보(KLAEBO): 금 {current_klaebo_gold}개"
    report.append(athlete_msg)

    send_telegram("\n\n".join(report))

    # --- 4. 상태 저장 ---
    with open('last_state.json', 'w', encoding='utf-8') as f:
        json.dump({
            "max_gold": current_max_gold,
            "klaebo_gold": current_klaebo_gold,
            "top_names": current_top_names
        }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    monitor()
