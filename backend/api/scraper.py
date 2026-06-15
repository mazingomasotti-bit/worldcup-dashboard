# 爬虫控制 API

from flask import Blueprint, jsonify
from datetime import datetime
from backend.database import query, execute
from backend.scraper.jingcai import JingcaiScraper
from backend.scraper.fivehundred import FiveHundredScraper

scraper_bp = Blueprint("scraper", __name__)


@scraper_bp.route("/scrape/trigger", methods=["POST"])
def trigger_scrape():
    now = datetime.now().isoformat()
    results = {"jingcai": "skipped", "fivehundred": "skipped", "time": now}

    try:
        jc = JingcaiScraper()
        jc.scrape_all()
        results["jingcai"] = "ok"
    except Exception as e:
        results["jingcai"] = f"error: {e}"

    try:
        fh = FiveHundredScraper()
        fh.scrape_odds()
        results["fivehundred"] = "ok"
    except Exception as e:
        results["fivehundred"] = f"error: {e}"

    execute(
        "INSERT OR REPLACE INTO strategy_config (key, value) VALUES (?, ?)",
        ("last_scrape", now)
    )
    return jsonify(results)


@scraper_bp.route("/scrape/status")
def scrape_status():
    row = None
    try:
        from backend.database import query_one
        row = query_one(
            "SELECT value FROM strategy_config WHERE key='last_scrape'"
        )
    except:
        pass

    match_count = query("SELECT COUNT(*) as c FROM matches")[0]["c"]
    odds_count = query("SELECT COUNT(*) as c FROM odds")[0]["c"]
    odds_jc = query("SELECT COUNT(*) as c FROM odds WHERE source='jingcai'")[0]["c"]
    odds_fh = query("SELECT COUNT(*) as c FROM odds WHERE source='fivehundred'")[0]["c"]

    return jsonify({
        "last_scrape": row["value"] if row else None,
        "match_count": match_count,
        "odds_count": odds_count,
        "odds_jingcai": odds_jc,
        "odds_fivehundred": odds_fh
    })
