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
    if not sorted_list:
        return f"📊 *{title}*\n데이터를 불러올 수 없습니다."
    
    table = f"📊 *{title}*\n"
    table += "`순위. NOC | 금 | 은 | 동 | 합계`\n"
    table += "---------------------------\n"
    
    top5 = sorted_list[:5]
    for i, m in enumerate(top5):
        table += f"{i+1}. {m['organisation']} | {m['gold']} | {m['silver']} | {m['bronze']} | {m['total']}\n"
    
    target_codes = ['KOR', 'JPN']
    top5_codes = [m['organisation'] for m in top5]
    
    extra_targets = []
    for idx, m in enumerate(sorted_list):
        if m['organisation'] in target_codes and m['organisation'] not in top5_codes:
            extra_targets.append((idx + 1, m))
    
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

    # --- 1. 국가별 순위 분석 ---
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
    sort_gold = sorted(processed_medals, key=lambda x: (-x['gold'], -x['silver'], -x['bronze']))
    sort_total = sorted(processed_medals, key=lambda x: (-x['total'], -x['gold']))

    # --- 2. 선수별 기록 분석 ---
    athletes = data_athletes.get('athletes', [])
    max_gold = max(a['medalsGold'] for a in athletes) if athletes else 0
    top_tv_names = sorted([a['tvName'] for a in athletes if a['medalsGold'] == max_gold])
    
    klaebo = next((a for a in athletes if "KLAEBO" in a['fullName']), None)
    if klaebo:
        klaebo_info = f"🎿 *KLAEBO*: 금 {klaebo['medalsGold']} | 은 {klaebo['medalsSilver']} | 동 {klaebo['medalsBronze']} (합 {klaebo['medalsTotal']})"
    else:
        klaebo_info = "🎿 *KLAEBO*: 정보 없음"

    # --- 3. 대한민국 메달리스트 상세 (날짜 역순 정렬) ---
    kor_medals = []
    for a in [at for at in athletes if at['organisation'] == 'KOR']:
        for m in a.get('medals', []):
            kor_medals.append({
                'tvName': a['tvName'],
                'sport': m.get('disciplineName', 'N/A'),
                'event': m.get('eventName', 'N/A'),
                'type': m['medalType'].replace('ME_', '').title(),
                'date': m.get('date', '0000-00-00')
            })
    
    # 날짜(date) 기준으로 내림차순 정렬 (새로운 메달이 앞)
    kor_medals.sort(key=lambda x: x['date'], reverse=True)

    kor_summary = "🇰🇷 *대한민국 메달리스트 상세*\n"
    if kor_medals:
        for km in kor_medals:
            kor_summary += f"• [{km['date']}] {km['tvName']} | {km['sport']} - {km['event']} | {km['type']}\n"
    else:
        kor_summary += "획득한 메달이 없습니다."

    # --- 4. 리포트 생성 ---
    report = []
    report.append(format_medal_table("금메달 순위 (TOP 5 + α)", sort_gold))
    report.append(format_medal_table("합계 순위 (TOP 5 + α)", sort_total))
    
    athlete_msg = "👤 *주요 선수 기록*\n"
    athlete_msg += f"🥇 최다 금메달 ({max_gold}개): {', '.join(top_tv_names)}\n"
    athlete_msg += klaebo_info
    report.append(athlete_msg)
    report.append(kor_summary)

    send_telegram("\n\n".join(report))

    # --- 5. 상태 저장 ---
    with open('last_state.json', 'w', encoding='utf-8') as f:
        json.dump({
            "max_gold": max_gold,
            "klaebo_gold": klaebo['medalsGold'] if klaebo else 0,
            "top_names": top_tv_names
        }, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    monitor()
