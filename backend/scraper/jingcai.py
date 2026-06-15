# 竞彩网爬虫（主力数据源）

import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from backend.scraper.base import BaseScraper
from backend.database import execute, query


class JingcaiScraper(BaseScraper):
    """爬取竞彩网足球赔率数据"""

    BASE_URL = "https://www.lottery.gov.cn"
    MATCH_URL = "https://www.lottery.gov.cn/jc/index.html"
    ODDS_API = "https://www.lottery.gov.cn/api/jc/sport/getFootballList"

    def scrape_matches(self):
        """抓取赛程数据"""
        try:
            resp = self.fetch(self.MATCH_URL, encoding="utf-8")
            if not resp:
                print("[jingcai] Failed to fetch match page")
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            matches = []
            # 尝试解析赛程表格（DOM结构依网站实际调整）
            items = soup.select(".match-item, .jc-match, tr[data-match]")
            for item in items:
                try:
                    mid = item.get("data-match") or item.get("data-id", "")
                    home = item.select_one(".home-team, .team-a")
                    away = item.select_one(".away-team, .team-b")
                    date_el = item.select_one(".match-date, .date")
                    time_el = item.select_one(".match-time, .time")

                    if home and away:
                        matches.append({
                            "match_id": mid,
                            "home": home.get_text(strip=True),
                            "away": away.get_text(strip=True),
                            "date": date_el.get_text(strip=True) if date_el else "",
                            "time": time_el.get_text(strip=True) if time_el else ""
                        })
                except Exception as e:
                    print(f"[jingcai] Parse error: {e}")
                    continue

            # 尝试通过API获取（更可靠）
            api_matches = self._fetch_api_matches()
            if api_matches:
                matches.extend(api_matches)

            print(f"[jingcai] Scraped {len(matches)} matches")
            return matches
        except Exception as e:
            print(f"[jingcai] scrape_matches error: {e}")
            return []

    def _fetch_api_matches(self):
        """尝试竞彩网内部API（JSON格式）"""
        try:
            resp = self.fetch(
                self.ODDS_API,
                params={"type": "1", "date": datetime.now().strftime("%Y-%m-%d")},
                encoding="utf-8"
            )
            if resp and resp.status_code == 200:
                data = resp.json()
                matches = []
                items = data.get("data", {}).get("list", []) if isinstance(data, dict) else []
                for item in items:
                    matches.append({
                        "match_id": str(item.get("matchId", "")),
                        "home": item.get("homeTeam", ""),
                        "away": item.get("awayTeam", ""),
                        "date": item.get("matchDate", ""),
                        "time": item.get("matchTime", "")
                    })
                return matches
        except Exception as e:
            print(f"[jingcai] API fetch error: {e}")
        return []

    def scrape_odds(self, match_id=None):
        """抓取赔率数据，支持3种玩法: spf / rspf / score"""
        try:
            resp = self.fetch(
                self.ODDS_API,
                params={
                    "type": "1",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "matchId": match_id or ""
                },
                encoding="utf-8"
            )
            if not resp or resp.status_code != 200:
                print(f"[jingcai] Failed to fetch odds")
                return []

            data = resp.json()
            odds_list = []
            items = data.get("data", {}).get("list", []) if isinstance(data, dict) else []

            for item in items:
                mid = str(item.get("matchId", ""))
                if match_id and mid != match_id:
                    continue

                # SPF 胜平负
                spf = item.get("spf", {}) or item.get("had", {})
                if spf:
                    odds_list.append({
                        "match_id": mid, "play_type": "spf",
                        "bet_option": "home", "odds_value": self._safe_float(spf.get("h") or spf.get("home")),
                        "handicap": 0
                    })
                    odds_list.append({
                        "match_id": mid, "play_type": "spf",
                        "bet_option": "draw", "odds_value": self._safe_float(spf.get("d") or spf.get("draw")),
                        "handicap": 0
                    })
                    odds_list.append({
                        "match_id": mid, "play_type": "spf",
                        "bet_option": "away", "odds_value": self._safe_float(spf.get("a") or spf.get("away")),
                        "handicap": 0
                    })

                # RSPF 让球胜平负
                rspf = item.get("rspf", {}) or item.get("hhad", {})
                handicap = self._safe_float(item.get("handicap", 0) or rspf.get("goal", 0))
                if rspf:
                    for opt, key in [("home", "h"), ("draw", "d"), ("away", "a")]:
                        odds_list.append({
                            "match_id": mid, "play_type": "rspf",
                            "bet_option": opt,
                            "odds_value": self._safe_float(rspf.get(key, 0)),
                            "handicap": handicap
                        })

                # 比分
                scores = item.get("crs", {}) or item.get("score", {})
                if scores:
                    for score_key, val in scores.items():
                        if score_key != "goal" and val:
                            odds_list.append({
                                "match_id": mid, "play_type": "score",
                                "bet_option": score_key.replace("_", ":"),
                                "odds_value": self._safe_float(val),
                                "handicap": 0
                            })

            self._save_odds_batch(odds_list, "jingcai")
            print(f"[jingcai] Scraped {len(odds_list)} odds entries")
            return odds_list
        except Exception as e:
            print(f"[jingcai] scrape_odds error: {e}")
            return []

    def _safe_float(self, val):
        try:
            return round(float(val), 2)
        except (TypeError, ValueError):
            return 0.0

    def _save_odds_batch(self, odds_list, source):
        now = datetime.now().isoformat()
        for o in odds_list:
            if o.get("odds_value", 0) > 0:
                execute(
                    """INSERT OR REPLACE INTO odds (match_id, source, play_type,
                       bet_option, odds_value, handicap, fetched_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (o["match_id"], source, o["play_type"],
                     o["bet_option"], o["odds_value"], o.get("handicap", 0), now)
                )

    def scrape_all(self):
        """全量抓取"""
        self.scrape_matches()
        self.scrape_odds()
