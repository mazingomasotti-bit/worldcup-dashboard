# 多源赔率交叉验证

from backend.database import query
from backend.config import ODDS_ANOMALY_THRESHOLD


def compare_match_odds(match_id):
    """比较某场比赛不同来源的赔率，返回差异标记"""
    sql = """SELECT play_type, bet_option, source, odds_value, handicap
             FROM odds WHERE match_id=? ORDER BY play_type, bet_option, source"""
    rows = query(sql, (match_id,))

    grouped = {}
    for r in rows:
        key = f"{r['play_type']}|{r['bet_option']}"
        if key not in grouped:
            grouped[key] = {"play_type": r["play_type"], "bet_option": r["bet_option"],
                            "handicap": r["handicap"], "sources": {}}
        grouped[key]["sources"][r["source"]] = r["odds_value"]

    result = []
    for k, v in grouped.items():
        vals = list(v["sources"].values())
        v["min"] = min(vals)
        v["max"] = max(vals)
        v["spread"] = round(v["max"] - v["min"], 2)
        v["anomaly"] = v["spread"] > ODDS_ANOMALY_THRESHOLD
        v["sources_count"] = len(vals)
        result.append(v)

    return result


def find_all_anomalies():
    """找出所有存在赔率异常的场次和玩法"""
    match_ids = [r["match_id"] for r in query("SELECT DISTINCT match_id FROM odds")]
    all_anomalies = []
    for mid in match_ids:
        compared = compare_match_odds(mid)
        anomalies = [c for c in compared if c.get("anomaly")]
        for a in anomalies:
            a["match_id"] = mid
        all_anomalies.extend(anomalies)
    return all_anomalies
