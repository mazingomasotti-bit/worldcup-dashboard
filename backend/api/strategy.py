# 稳健策略 API

import json
import itertools
from flask import Blueprint, request, jsonify
from backend.database import query, query_one, execute
from backend.config import (
    DEFAULT_PRINCIPAL, DEFAULT_BET_RATIO, DEFAULT_STOP_LOSS,
    DEFAULT_TAKE_PROFIT, DEFAULT_ODDS_MIN, DEFAULT_ODDS_MAX,
    DEFAULT_WEEKLY_LIMIT, COMBO_3X4_ODDS_MIN, COMBO_3X4_ODDS_MAX
)

strategy_bp = Blueprint("strategy", __name__)


def _get_config():
    rows = query("SELECT key, value FROM strategy_config")
    cfg = {r["key"]: r["value"] for r in rows}
    if not cfg:
        # 初始化默认配置
        defaults = {
            "total_principal": DEFAULT_PRINCIPAL,
            "bet_ratio": DEFAULT_BET_RATIO,
            "stop_loss_ratio": DEFAULT_STOP_LOSS,
            "take_profit_ratio": DEFAULT_TAKE_PROFIT,
            "odds_min": DEFAULT_ODDS_MIN,
            "odds_max": DEFAULT_ODDS_MAX,
            "weekly_limit": DEFAULT_WEEKLY_LIMIT,
        }
        for k, v in defaults.items():
            execute("INSERT OR IGNORE INTO strategy_config (key, value) VALUES (?, ?)", (k, v))
        return defaults
    return cfg


@strategy_bp.route("/strategy/recommend")
def recommend():
    cfg = _get_config()
    odds_min = cfg.get("odds_min", DEFAULT_ODDS_MIN)
    odds_max = cfg.get("odds_max", DEFAULT_ODDS_MAX)

    sql = """SELECT m.*, o.odds_value, o.bet_option
             FROM matches m
             JOIN odds o ON m.match_id = o.match_id
             WHERE m.status = 'upcoming'
               AND o.play_type = 'spf'
               AND o.source = 'jingcai'
               AND o.odds_value BETWEEN ? AND ?
             ORDER BY m.match_date, ABS(o.odds_value - 1.85)"""
    rows = query(sql, (odds_min, odds_max))

    # 去重（同一场比赛取最接近1.85的赔率那个选项）
    seen = {}
    for r in rows:
        mid = r["match_id"]
        if mid not in seen:
            seen[mid] = r
    return jsonify(list(seen.values()))


@strategy_bp.route("/strategy/simulate")
def simulate():
    mode = request.args.get("mode", "2x1")
    match_ids = request.args.getlist("match_ids")

    if len(match_ids) < 2:
        return jsonify({"error": "至少需要2场比赛"}), 400

    picks = []
    total_odds = 1.0
    for mid in match_ids:
        odd = query_one(
            """SELECT o.odds_value, m.home_team, m.away_team, o.bet_option
               FROM odds o JOIN matches m ON o.match_id = m.match_id
               WHERE o.match_id=? AND o.play_type='spf' AND o.source='jingcai'
               ORDER BY o.odds_value""",
            (mid,)
        )
        if odd:
            picks.append(odd)
            total_odds *= odd["odds_value"]

    total_odds = round(total_odds, 2)
    cfg = _get_config()
    max_bet = round(cfg["total_principal"] * cfg["bet_ratio"], 2)
    potential = round(max_bet * total_odds, 2)

    return jsonify({
        "mode": mode,
        "picks": picks,
        "total_odds": total_odds,
        "max_bet": max_bet,
        "potential_return": potential
    })


@strategy_bp.route("/strategy/3x4")
def combo_3x4():
    """3串4推荐：从符合条件的比赛中找出最优3场组合"""
    sql = """SELECT m.match_id, m.home_team, m.away_team, m.match_date,
                    o.odds_value, o.bet_option
             FROM matches m
             JOIN odds o ON m.match_id = o.match_id
             WHERE m.status = 'upcoming'
               AND o.play_type = 'spf'
               AND o.source = 'jingcai'
               AND o.odds_value BETWEEN ? AND ?
               AND o.bet_option IN ('home', 'away')
             ORDER BY m.match_date"""
    rows = query(sql, (COMBO_3X4_ODDS_MIN, COMBO_3X4_ODDS_MAX))

    if len(rows) < 3:
        return jsonify({"error": "符合条件的比赛不足3场", "count": len(rows)})

    # 找出最优3场组合：赔率最接近(1.7+2.2)/2=1.95
    matches = list({r["match_id"]: r for r in rows}.values())
    best = None
    best_score = float("inf")
    for combo in itertools.combinations(matches, 3):
        odds = [c["odds_value"] for c in combo]
        score = sum(abs(o - 1.95) for o in odds) + abs(max(odds) - min(odds))
        if score < best_score:
            best_score = score
            best = combo

    if not best:
        return jsonify({"error": "无法生成推荐"}), 400

    odds_list = [c["odds_value"] for c in best]
    total_3x1 = round(reduce_mul(odds_list, 1.0), 2)
    pairs = [round(odds_list[0] * odds_list[1], 2),
             round(odds_list[0] * odds_list[2], 2),
             round(odds_list[1] * odds_list[2], 2)]
    cfg = _get_config()
    unit_bet = round(cfg["total_principal"] * cfg["bet_ratio"] / 4, 2)

    return jsonify({
        "matches": [{
            "match_id": c["match_id"],
            "home_team": c["home_team"],
            "away_team": c["away_team"],
            "match_date": c["match_date"],
            "odds": c["odds_value"],
            "pick": c["bet_option"]
        } for c in best],
        "odds_3x1": total_3x1,
        "odds_2x1_pairs": pairs,
        "unit_bet": unit_bet,
        "total_bet": round(unit_bet * 4, 2),
        "min_return": round(unit_bet * min(pairs), 2),
        "max_return": round(unit_bet * (total_3x1 + sum(pairs)), 2),
        "stability_score": round(10 - best_score, 1)
    })


def reduce_mul(lst, init):
    r = init
    for x in lst:
        r *= x
    return r


@strategy_bp.route("/strategy/fund-status")
def fund_status():
    cfg = _get_config()
    principal = cfg["total_principal"]
    bet_ratio = cfg["bet_ratio"]
    stop_loss = cfg["stop_loss_ratio"]
    take_profit = cfg["take_profit_ratio"]

    # 计算当前余额
    logs = query("SELECT * FROM fund_log ORDER BY date DESC, id DESC")
    if logs:
        balance = logs[0]["balance_after"]
    else:
        balance = principal
        execute(
            "INSERT INTO fund_log (date, type, amount, balance_before, balance_after, note) VALUES (?, ?, ?, ?, ?, ?)",
            ("2026-06-15", "deposit", principal, 0, principal, "初始本金")
        )

    # 本周投注次数
    week_bets = query(
        "SELECT COUNT(*) as cnt FROM bets WHERE created_at >= date('now', 'weekday 0', '-7 days')"
    )[0]["cnt"]
    weekly_limit = int(cfg["weekly_limit"])

    # 近期盈亏
    total_profit = sum(r["profit"] or 0 for r in query("SELECT profit FROM bets WHERE result != 'pending'"))
    current_balance = principal + total_profit
    pl_ratio = total_profit / principal if principal > 0 else 0
    max_bet = round(current_balance * bet_ratio, 2)

    # 预警状态
    alerts = []
    if pl_ratio <= -stop_loss:
        alerts.append({"level": "danger", "msg": f"亏损已达{abs(pl_ratio)*100:.0f}%，触发止损线！建议暂停投注"})
    elif pl_ratio <= -stop_loss * 0.7:
        alerts.append({"level": "warning", "msg": f"亏损{abs(pl_ratio)*100:.0f}%，接近止损线(-{stop_loss*100:.0f}%)"})
    if pl_ratio >= take_profit:
        alerts.append({"level": "success", "msg": f"盈利已达{pl_ratio*100:.0f}%，触发止盈线！建议转出盈利"})
    if week_bets >= weekly_limit:
        alerts.append({"level": "info", "msg": f"本周已投注{week_bets}次，已达上限"})

    # 连亏检测
    recent = query("SELECT result FROM bets WHERE result != 'pending' ORDER BY created_at DESC LIMIT 5")
    streak = 0
    for r in recent:
        if r["result"] == "lost":
            streak += 1
        else:
            break
    if streak >= 2:
        alerts.append({"level": "danger", "msg": f"连亏{streak}场！建议冷静"})

    return jsonify({
        "principal": principal,
        "current_balance": round(current_balance, 2),
        "total_profit": round(total_profit, 2),
        "pl_ratio": round(pl_ratio * 100, 1),
        "max_bet_per_time": max_bet,
        "week_bets": week_bets,
        "weekly_limit": weekly_limit,
        "stop_loss_line": round(principal * (1 - stop_loss), 2),
        "take_profit_line": round(principal * (1 + take_profit), 2),
        "alerts": alerts
    })


@strategy_bp.route("/strategy/config", methods=["PUT"])
def update_config():
    data = request.get_json()
    allowed = {"total_principal", "bet_ratio", "stop_loss_ratio",
               "take_profit_ratio", "odds_min", "odds_max", "weekly_limit"}
    for k, v in data.items():
        if k in allowed:
            execute("INSERT OR REPLACE INTO strategy_config (key, value) VALUES (?, ?)", (k, float(v)))
    return jsonify({"ok": True, "config": _get_config()})
