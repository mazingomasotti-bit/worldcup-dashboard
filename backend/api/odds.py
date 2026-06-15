# 赔率 API（3种玩法：spf / rspf / score）

from flask import Blueprint, request, jsonify
from backend.database import query
from backend.config import ODDS_ANOMALY_THRESHOLD

odds_bp = Blueprint("odds", __name__)


@odds_bp.route("/odds")
def list_odds():
    match_id = request.args.get("match_id")
    play_type = request.args.get("play_type")
    source = request.args.get("source")

    sql = """SELECT o.*, m.home_team, m.away_team, m.match_date, m.status
             FROM odds o JOIN matches m ON o.match_id = m.match_id WHERE 1=1"""
    params = []
    if match_id:
        sql += " AND o.match_id=?"
        params.append(match_id)
    if play_type:
        sql += " AND o.play_type=?"
        params.append(play_type)
    if source:
        sql += " AND o.source=?"
        params.append(source)
    sql += " ORDER BY m.match_date, o.play_type, o.bet_option"

    return jsonify(query(sql, params))


@odds_bp.route("/odds/compare")
def compare_odds():
    match_id = request.args.get("match_id")
    if not match_id:
        return jsonify({"error": "match_id required"}), 400

    sql = """SELECT o.play_type, o.bet_option, o.odds_value, o.source, o.handicap
             FROM odds o WHERE o.match_id=?
             ORDER BY o.play_type, o.bet_option, o.source"""
    rows = query(sql, (match_id,))

    result = {}
    for r in rows:
        pt = r["play_type"]
        bo = r["bet_option"]
        key = f"{pt}|{bo}"
        if key not in result:
            result[key] = {"play_type": pt, "bet_option": bo,
                           "handicap": r["handicap"], "sources": {}}
        result[key]["sources"][r["source"]] = r["odds_value"]

    # 异常检测
    for k, v in result.items():
        vals = list(v["sources"].values())
        v["anomaly"] = len(vals) >= 2 and abs(vals[0] - vals[1]) > ODDS_ANOMALY_THRESHOLD

    return jsonify(list(result.values()))


@odds_bp.route("/odds/anomaly")
def anomaly_odds():
    rows = query("SELECT DISTINCT match_id FROM odds")
    anomalies = []
    for r in rows:
        compare = compare_odds_internal(r["match_id"])
        anomalies.extend([c for c in compare if c.get("anomaly")])
    return jsonify(anomalies)


def compare_odds_internal(match_id):
    sql = """SELECT o.play_type, o.bet_option, o.odds_value, o.source, o.handicap
             FROM odds o WHERE o.match_id=? ORDER BY o.play_type, o.bet_option, o.source"""
    rows = query(sql, (match_id,))
    result = {}
    for r in rows:
        key = f"{r['play_type']}|{r['bet_option']}"
        if key not in result:
            result[key] = {"play_type": r["play_type"], "bet_option": r["bet_option"],
                           "handicap": r["handicap"], "match_id": match_id, "sources": {}}
        result[key]["sources"][r["source"]] = r["odds_value"]
    for v in result.values():
        vals = list(v["sources"].values())
        v["anomaly"] = len(vals) >= 2 and abs(vals[0] - vals[1]) > ODDS_ANOMALY_THRESHOLD
    return list(result.values())
