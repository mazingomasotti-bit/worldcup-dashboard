# Flask 入口

import os
from flask import Flask, render_template
from backend.database import init_db, query
from backend.api.matches import matches_bp
from backend.api.odds import odds_bp
from backend.api.teams import teams_bp
from backend.api.bets import bets_bp
from backend.api.strategy import strategy_bp
from backend.api.scraper import scraper_bp


def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__,
                template_folder=os.path.join(base_dir, "frontend", "templates"),
                static_folder=os.path.join(base_dir, "frontend", "static"))

    app.register_blueprint(matches_bp, url_prefix="/api")
    app.register_blueprint(odds_bp, url_prefix="/api")
    app.register_blueprint(teams_bp, url_prefix="/api")
    app.register_blueprint(bets_bp, url_prefix="/api")
    app.register_blueprint(strategy_bp, url_prefix="/api")
    app.register_blueprint(scraper_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return render_template("index.html")

    init_db()

    # 首次启动自动播种模拟数据
    try:
        count = query("SELECT COUNT(*) as c FROM matches")[0]["c"]
        if count == 0:
            import runpy
            seed_path = os.path.join(base_dir, "seed_data.py")
            runpy.run_path(seed_path)
    except Exception as e:
        print(f"[auto-seed] {e}")

    return app
