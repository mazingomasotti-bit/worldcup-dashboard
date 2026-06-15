# 球队 + 积分榜 API

import json
from flask import Blueprint, request, jsonify
from backend.database import query, query_one

teams_bp = Blueprint("teams", __name__)


@teams_bp.route("/standings")
def list_standings():
    group = request.args.get("group")
    sql = "SELECT * FROM standings"
    params = []
    if group:
        sql += " WHERE group_name=?"
        params.append(group)
    sql += " ORDER BY group_name, points DESC, (goals_for - goals_against) DESC"
    return jsonify(query(sql, params))


@teams_bp.route("/teams")
def list_teams():
    rows = query("SELECT * FROM teams ORDER BY group_name, team_name")
    for r in rows:
        if r.get("recent_form"):
            r["recent_form"] = json.loads(r["recent_form"])
    return jsonify(rows)


@teams_bp.route("/teams/<team_name>")
def get_team(team_name):
    t = query_one("SELECT * FROM teams WHERE team_name=?", (team_name,))
    if not t:
        return jsonify({"error": "not found"}), 404
    if t.get("recent_form"):
        t["recent_form"] = json.loads(t["recent_form"])
    s = query_one("SELECT * FROM standings WHERE team_name=?", (team_name,))
    t["standing"] = s
    return jsonify(t)
