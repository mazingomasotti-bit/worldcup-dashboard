# 500.com 爬虫（交叉验证备用）

import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from backend.scraper.base import BaseScraper
from backend.database import execute


class FiveHundredScraper(BaseScraper):
    """爬取500.com足球赔率数据，用于与竞彩网交叉验证"""

    BASE_URL = "https://live.500.com"
    ODDS_URL = "https://odds.500.com/fenxi/ouzhi-{}.shtml"
    SCORE_URL = "https://odds.500.com/fenxi/bifen-{}.shtml"
    LIST_URL = "https://live.500.com/?e={}"

    def scrape_odds(self, match_id=None):
        """抓取赔率数据"""
        odds_list = []

        try:
            # 先获取赛程列表
            resp = self.fetch(self.LIST_URL.format(datetime.now().strftime("%Y-%m-%d")),
                            encoding="gb2312")
            if not resp:
                print("[500.com] Failed to fetch match list")
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            match_links = soup.select("a[href*='fenxi/ouzhi-']")

            for link in match_links:
                href = link.get("href", "")
                fid_match = re.search(r'ouzhi-(\d+)', href)
                if not fid_match:
                    continue
                fid = fid_match.group(1)

                if match_id and fid != match_id:
                    continue

                # 抓取欧赔（SPF）
                try:
                    spf_odds = self._scrape_spf(fid)
                    odds_list.extend(spf_odds)
                except Exception as e:
                    print(f"[500.com] SPF error for {fid}: {e}")

                # 抓取让球盘
                try:
                    rspf_odds = self._scrape_rspf(fid)
                    odds_list.extend(rspf_odds)
                except Exception as e:
                    print(f"[500.com] RSPF error for {fid}: {e}")

                # 抓取比分赔率
                try:
                    score_odds = self._scrape_score(fid)
                    odds_list.extend(score_odds)
                except Exception as e:
                    print(f"[500.com] Score error for {fid}: {e}")

            self._save_odds_batch(odds_list)
            print(f"[500.com] Scraped {len(odds_list)} odds entries")
            return odds_list

        except Exception as e:
            print(f"[500.com] scrape_odds error: {e}")
            return []

    def _scrape_spf(self, fid):
        """抓取胜平负赔率"""
        url = self.ODDS_URL.format(fid)
        resp = self.fetch(url, encoding="gb2312")
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        odds = []

        # 解析欧赔表格（取主流博彩公司平均赔率）
        rows = soup.select("table.odds-table tr, table#table_1 tr")
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 4:
                try:
                    home = float(cols[1].get_text(strip=True))
                    draw = float(cols[2].get_text(strip=True))
                    away = float(cols[3].get_text(strip=True))
                    if home > 1.0 and draw > 1.0 and away > 1.0:
                        odds.extend([
                            {"match_id": fid, "play_type": "spf",
                             "bet_option": "home", "odds_value": home, "handicap": 0},
                            {"match_id": fid, "play_type": "spf",
                             "bet_option": "draw", "odds_value": draw, "handicap": 0},
                            {"match_id": fid, "play_type": "spf",
                             "bet_option": "away", "odds_value": away, "handicap": 0},
                        ])
                        break  # 取第一家公司即可
                except ValueError:
                    continue
        return odds

    def _scrape_rspf(self, fid):
        """抓取让球胜平负赔率"""
        url = f"https://odds.500.com/fenxi/yazhi-{fid}.shtml"
        resp = self.fetch(url, encoding="gb2312")
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        odds = []

        # 解析亚盘让球数和赔率
        rows = soup.select("table.odds-table tr, table#table_1 tr")
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 4:
                try:
                    handicap_text = cols[1].get_text(strip=True)
                    handicap = self._parse_handicap(handicap_text)
                    home_odds = float(cols[2].get_text(strip=True))
                    away_odds = float(cols[3].get_text(strip=True))
                    draw_odds = round((home_odds + away_odds) / 2, 2)

                    if home_odds > 1.0:
                        odds.extend([
                            {"match_id": fid, "play_type": "rspf",
                             "bet_option": "home", "odds_value": home_odds, "handicap": handicap},
                            {"match_id": fid, "play_type": "rspf",
                             "bet_option": "draw", "odds_value": draw_odds, "handicap": handicap},
                            {"match_id": fid, "play_type": "rspf",
                             "bet_option": "away", "odds_value": away_odds, "handicap": handicap},
                        ])
                        break
                except ValueError:
                    continue
        return odds

    def _scrape_score(self, fid):
        """抓取比分赔率"""
        url = self.SCORE_URL.format(fid)
        resp = self.fetch(url, encoding="gb2312")
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        odds = []

        rows = soup.select("table.odds-table tr, table#table_1 tr")
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 3:
                try:
                    score_text = cols[0].get_text(strip=True).replace("-", ":")
                    val = float(cols[1].get_text(strip=True))
                    if val > 1.0 and ":" in score_text:
                        odds.append({
                            "match_id": fid, "play_type": "score",
                            "bet_option": score_text, "odds_value": val, "handicap": 0
                        })
                except ValueError:
                    continue
        return odds

    def _parse_handicap(self, text):
        """解析让球数文本 → 数值，如 '半球'→0.5, '一球'→1.0"""
        mapping = {
            "平手": 0, "平半": 0.25,
            "半球": 0.5, "半一": 0.75,
            "一球": 1.0, "一球/球半": 1.25,
            "球半": 1.5, "球半/两球": 1.75,
            "两球": 2.0,
        }
        for k, v in mapping.items():
            if k in text:
                sign = -1 if "受" in text else 1
                return round(sign * v, 2)
        try:
            return float(text)
        except ValueError:
            return 0

    def _save_odds_batch(self, odds_list):
        """保存赔率到数据库"""
        now = datetime.now().isoformat()
        for o in odds_list:
            if o.get("odds_value", 0) > 0:
                execute(
                    """INSERT OR REPLACE INTO odds (match_id, source, play_type,
                       bet_option, odds_value, handicap, fetched_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (o["match_id"], "fivehundred", o["play_type"],
                     o["bet_option"], o["odds_value"], o.get("handicap", 0), now)
                )
