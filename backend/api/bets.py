# 竞猜追踪 API

import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.database import query, query_one, execute
from backend.services.fund_manager import check_bet_limit, record_bet, settle_bet

bets_bp = Blueprint("bets", __name__)


@bets_bp.route("/bets")
def list_bets():
    status = request.args.get("status")
    bet_type = request.args.get("bet_type")
    sql = "SELECT * FROM bets WHERE 1=1"
    params = []
    if status:
        sql += " AND result=?"
        params.append(status)
    if bet_type:
        sql += " AND bet_type=?"
        params.append(bet_type)
    sql += " ORDER BY created_at DESC"
    rows = query(sql, params)
    for r in rows:
        if r.get("matches"):
            r["matches"] = json.loads(r["matches"])
    return jsonify(rows)


@bets_bp.route("/bets", methods=["POST"])
def create_bet():
    data = request.get_json()
    bet_type = data.get("bet_type", "single")
    play_type = data.get("play_type", "spf")
    matches = data.get("matches", [])
    amount = float(data.get("amount", 0))
    total_odds = float(data.get("total_odds", 0))

    if amount <= 0:
        return jsonify({"error": "下注金额必须大于0"}), 400

    # 检查5%上限
    limit = check_bet_limit(amount)
    if limit.get("blocked"):
        return jsonify({"error": limit["reason"]}), 400

    potential_return = round(amount * total_odds, 2)
    bet_id = execute(
        """INSERT INTO bets (bet_type, play_type, bet_date, matches, amount,
           total_odds, potential_return, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (bet_type, play_type, datetime.now().strftime("%Y-%m-%d"),
         json.dumps(matches, ensure_ascii=False), amount, total_odds,
         potential_return, datetime.now().isoformat())
    )
    record_bet(bet_id, amount, json.dumps(matches, ensure_ascii=False))
    return jsonify({"id": bet_id, "potential_return": potential_return, **limit}), 201


@bets_bp.route("/bets/<int:bet_id>/settle", methods=["PUT"])
def settle(bet_id):
    data = request.get_json()
    actual_return = float(data.get("actual_return", 0))
    bet = query_one("SELECT * FROM bets WHERE id=?", (bet_id,))
    if not bet:
        return jsonify({"error": "not found"}), 404
    profit = round(actual_return - bet["amount"], 2)
    result = "won" if profit > 0 else ("lost" if profit < 0 else "partial")
    execute(
        "UPDATE bets SET result=?, actual_return=?, profit=? WHERE id=?",
        (result, actual_return, profit, bet_id)
    )
    settle_bet(bet_id, profit, json.loads(bet["matches"]) if bet["matches"] else [])
    return jsonify({"id": bet_id, "result": result, "profit": profit})


@bets_bp.route("/bets/stats")
def stats():
    rows = query("SELECT result, amount, profit, bet_type FROM bets WHERE result != 'pending'")
    total_bets = len(rows)
    total_amount = sum(r["amount"] for r in rows)
    total_profit = sum(r["profit"] for r in rows)
    won = sum(1 for r in rows if r["result"] == "won")
    win_rate = round(won / total_bets * 100, 1) if total_bets else 0
    roi = round(total_profit / total_amount * 100, 1) if total_amount else 0
    return jsonify({
        "total_bets": total_bets,
        "total_amount": round(total_amount, 2),
        "total_profit": round(total_profit, 2),
        "win_rate": win_rate,
        "roi": roi
    })
