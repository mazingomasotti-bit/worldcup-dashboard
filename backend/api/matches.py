# 赛程 API

from flask import Blueprint, request, jsonify
from backend.database import query, query_one

matches_bp = Blueprint("matches", __name__)


@matches_bp.route("/matches")
def list_matches():
    stage = request.args.get("stage")
    date = request.args.get("date")
    status = request.args.get("status")
    group = request.args.get("group")

    sql = "SELECT * FROM matches WHERE 1=1"
    params = []
    if stage:
        sql += " AND stage=?"
        params.append(stage)
    if date:
        sql += " AND match_date=?"
        params.append(date)
    if status:
        sql += " AND status=?"
        params.append(status)
    if group:
        sql += " AND group_name=?"
        params.append(group)
    sql += " ORDER BY match_date, match_time"

    return jsonify(query(sql, params))


@matches_bp.route("/matches/<match_id>")
def get_match(match_id):
    m = query_one("SELECT * FROM matches WHERE match_id=?", (match_id,))
    if not m:
        return jsonify({"error": "not found"}), 404
    w = query_one("SELECT * FROM weather WHERE match_id=?", (match_id,))
    m["weather"] = w
    return jsonify(m)
