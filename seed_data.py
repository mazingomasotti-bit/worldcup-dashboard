# 模拟数据导入脚本 — 2026世界杯
import sys, os, random, json
sys.path.insert(0, os.path.dirname(__file__))
from backend.database import init_db, execute, query
from datetime import datetime, timedelta

init_db()

# ====== 48支球队（2026世界杯12组） ======
groups = {
    "A": [("美国", 11, "东道主"), ("葡萄牙", 6, "争冠热门"), ("埃及", 32, "非洲劲旅"), ("新西兰", 95, "大洋洲代表")],
    "B": [("加拿大", 35, "东道主"), ("德国", 4, "争冠热门"), ("韩国", 23, "亚洲劲旅"), ("巴拿马", 58, "中北美黑马")],
    "C": [("墨西哥", 14, "东道主"), ("意大利", 8, "欧洲劲旅"), ("澳大利亚", 27, "亚洲代表"), ("喀麦隆", 43, "非洲雄狮")],
    "D": [("法国", 2, "卫冕冠军"), ("丹麦", 19, "北欧劲旅"), ("摩洛哥", 13, "非洲黑马"), ("秘鲁", 33, "南美代表")],
    "E": [("巴西", 3, "夺冠热门"), ("瑞士", 17, "欧洲劲旅"), ("尼日利亚", 36, "非洲雄鹰"), ("中国", 88, "亚洲之龙")],
    "F": [("阿根廷", 1, "卫冕美洲冠军"), ("荷兰", 7, "无冕之王"), ("日本", 20, "亚洲劲旅"), ("牙买加", 54, "加勒比旋风")],
    "G": [("英格兰", 5, "争冠热门"), ("乌拉圭", 15, "南美劲旅"), ("伊朗", 22, "亚洲劲旅"), ("加拿大2", 38, "中北美势力")],  # placeholder
    "H": [("西班牙", 9, "传控之王"), ("克罗地亚", 10, "格子军团"), ("塞内加尔", 18, "非洲冠军"), ("阿联酋", 67, "亚洲黑马")],
    "I": [("比利时", 12, "黄金一代"), ("哥伦比亚", 16, "南美劲旅"), ("波兰", 26, "东欧铁骑"), ("伊拉克", 61, "亚洲代表")],
    "J": [("塞维利亚", 21, "东欧劲旅"), ("智利", 29, "南美红军"), ("加纳", 41, "非洲之星"), ("卡塔尔", 55, "亚洲东道主")],
    "K": [("挪威", 24, "北欧海盗"), ("土耳其", 31, "星月军团"), ("马里", 45, "非洲黑马"), ("沙特", 51, "亚洲绿隼")],
    "L": [("苏格兰", 30, "风笛军团"), ("匈牙利", 28, "东欧劲旅"), ("南非", 62, "非洲代表"), ("哥斯达黎加", 39, "中北美黑马")],
}

# Fix "加拿大2" → "科特迪瓦" and "塞维利亚" → "塞尔维亚"
groups["G"] = [("英格兰", 5, "争冠热门"), ("乌拉圭", 15, "南美劲旅"), ("伊朗", 22, "亚洲劲旅"), ("科特迪瓦", 38, "非洲大象")]
groups["J"] = [("塞尔维亚", 21, "东欧劲旅"), ("智利", 29, "南美红军"), ("加纳", 41, "非洲之星"), ("卡塔尔", 55, "亚洲东道主")]

# ====== 插入球队和积分榜 ======
all_teams = []
for g, teams in groups.items():
    for name, rank, note in teams:
        all_teams.append(name)
        execute("INSERT OR IGNORE INTO teams (team_name, fifa_rank, group_name, recent_form, notes) VALUES (?,?,?,?,?)",
                (name, rank, g, json.dumps(random.choices(["W","D","L"], k=5)), note))
        execute("INSERT OR IGNORE INTO standings (group_name, team_name, played, won, drawn, lost, goals_for, goals_against, points) VALUES (?,?,?,?,?,?,?,?,?)",
                (g, name, random.randint(1,3), random.randint(0,2), random.randint(0,2), random.randint(0,2),
                 random.randint(1,6), random.randint(0,5), random.randint(1,7)))

# ====== 生成赛程（2026/6/11 - 2026/7/19） ======
base = datetime(2026, 6, 11)
match_id_counter = [0]

def make_match(stage, group, home, away, d, t, focus=False):
    match_id_counter[0] += 1
    mid = f"WC2026_{match_id_counter[0]:03d}"
    execute("""INSERT OR IGNORE INTO matches (match_id, stage, group_name, match_date, match_time, home_team, away_team, status, is_focus_match)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (mid, stage, group, d.strftime("%Y-%m-%d"), t, home, away, "upcoming", 1 if focus else 0))
    return mid

# 小组赛第1轮（6/11-6/14）
for g, teams in groups.items():
    d = base + timedelta(days=list(groups.keys()).index(g))
    make_match("group", g, teams[0][0], teams[1][0], d, "18:00", focus=teams[0][1]<=10 or teams[1][1]<=10)
    make_match("group", g, teams[2][0], teams[3][0], d, "21:00", focus=False)

# 小组赛第2轮（6/16-6/19）
d2 = base + timedelta(days=5)
for g, teams in groups.items():
    d = d2 + timedelta(days=list(groups.keys()).index(g))
    make_match("group", g, teams[0][0], teams[2][0], d, "18:00", focus=teams[0][1]<=10)
    make_match("group", g, teams[1][0], teams[3][0], d, "21:00")

# 小组赛第3轮（6/21-6/24）
d3 = base + timedelta(days=10)
for g, teams in groups.items():
    d = d3 + timedelta(days=list(groups.keys()).index(g))
    make_match("group", g, teams[0][0], teams[3][0], d, "18:00")
    make_match("group", g, teams[1][0], teams[2][0], d, "21:00")

# 淘汰赛（占位）
stages = [("round16", "1/8决赛", 15), ("quarter", "1/4决赛", 22), ("semi", "半决赛", 28), ("final", "决赛", 36)]
for stage, sname, offset in stages:
    d = base + timedelta(days=offset)
    make_match(stage, None, "待定", "待定", d, "20:00")

print(f"Inserted {match_id_counter[0]} matches, {len(all_teams)} teams")

# ====== 生成模拟赔率（3种玩法） ======
matches = query("SELECT match_id, home_team, away_team FROM matches WHERE stage='group'")
odds_count = 0
for m in matches:
    mid = m["match_id"]
    now = datetime.now().isoformat()

    # SPF 赔率（3项：home/draw/away）
    home_odds = round(random.uniform(1.4, 3.5), 2)
    draw_odds = round(random.uniform(2.5, 4.5), 2)
    away_odds = round(random.uniform(2.0, 5.0), 2)
    for opt, val in [("home", home_odds), ("draw", draw_odds), ("away", away_odds)]:
        execute("INSERT OR REPLACE INTO odds (match_id, source, play_type, bet_option, odds_value, handicap, fetched_at) VALUES (?,?,?,?,?,?,?)",
                (mid, "jingcai", "spf", opt, val, 0, now))
        # 500.com 略有不一致（模拟交叉验证）
        val500 = round(val + random.uniform(-0.15, 0.15), 2)
        execute("INSERT OR REPLACE INTO odds (match_id, source, play_type, bet_option, odds_value, handicap, fetched_at) VALUES (?,?,?,?,?,?,?)",
                (mid, "fivehundred", "spf", opt, val500, 0, now))
        odds_count += 2

    # RSPF 赔率（让球，随机-1/0/+1/+2盘口）
    handicap = random.choice([-1, 0, 1, 2])
    for opt, val in [("home", round(random.uniform(1.5, 4.0), 2)),
                      ("draw", round(random.uniform(3.0, 5.0), 2)),
                      ("away", round(random.uniform(1.8, 4.5), 2))]:
        execute("INSERT OR REPLACE INTO odds (match_id, source, play_type, bet_option, odds_value, handicap, fetched_at) VALUES (?,?,?,?,?,?,?)",
                (mid, "jingcai", "rspf", opt, val, handicap, now))
        execute("INSERT OR REPLACE INTO odds (match_id, source, play_type, bet_option, odds_value, handicap, fetched_at) VALUES (?,?,?,?,?,?,?)",
                (mid, "fivehundred", "rspf", opt, round(val + random.uniform(-0.12, 0.12), 2), handicap, now))
        odds_count += 2

    # 比分赔率（31项，选代表性比分）
    score_options = ["1:0","2:0","2:1","3:0","3:1","3:2","0:0","1:1","2:2","3:3",
                     "0:1","0:2","1:2","0:3","1:3","2:3","4:0","4:1","0:4","1:4",
                     "5:0","5:1","0:5","1:5","4:2","2:4","4:3","3:4","5:2","2:5","其他"]
    for opt in score_options:
        val = round(random.uniform(5.0, 50.0), 1) if opt != "其他" else round(random.uniform(80, 200), 1)
        execute("INSERT OR REPLACE INTO odds (match_id, source, play_type, bet_option, odds_value, handicap, fetched_at) VALUES (?,?,?,?,?,?,?)",
                (mid, "jingcai", "score", opt, val, 0, now))
        odds_count += 1

print(f"Inserted {odds_count} odds rows")

# ====== 策略配置默认值 ======
configs = [
    ("total_principal", 200.0), ("bet_ratio", 0.05), ("stop_loss_ratio", 0.15),
    ("take_profit_ratio", 0.30), ("odds_min", 1.6), ("odds_max", 2.0),
    ("weekly_limit", 3), ("combo_3x4_odds_min", 1.7), ("combo_3x4_odds_max", 2.2)
]
for k, v in configs:
    execute("INSERT OR IGNORE INTO strategy_config (key, value) VALUES (?,?)", (k, v))

print("Seed data complete!")
print(f"  Teams: {len(all_teams)}")
print(f"  Matches: {match_id_counter[0]}")
print(f"  Odds: {odds_count}")
