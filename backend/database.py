# SQLite 数据库初始化 + 工具函数

import sqlite3
import os
from backend.config import DATABASE_PATH

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_PATH)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            match_id TEXT UNIQUE,
            stage TEXT,
            group_name TEXT,
            match_date TEXT,
            match_time TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT DEFAULT 'upcoming',
            is_focus_match INTEGER DEFAULT 0,
            city TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS odds (
            id INTEGER PRIMARY KEY,
            match_id TEXT,
            source TEXT,
            play_type TEXT,
            bet_option TEXT,
            odds_value REAL,
            handicap REAL,
            fetched_at TEXT,
            UNIQUE(match_id, source, play_type, bet_option)
        );

        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            team_name TEXT UNIQUE,
            fifa_rank INTEGER,
            group_name TEXT,
            recent_form TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY,
            group_name TEXT,
            team_name TEXT,
            played INTEGER DEFAULT 0,
            won INTEGER DEFAULT 0,
            drawn INTEGER DEFAULT 0,
            lost INTEGER DEFAULT 0,
            goals_for INTEGER DEFAULT 0,
            goals_against INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            UNIQUE(group_name, team_name)
        );

        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY,
            match_id TEXT UNIQUE,
            weather_desc TEXT,
            temperature INTEGER,
            warning INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY,
            bet_type TEXT,
            play_type TEXT,
            bet_date TEXT,
            matches TEXT,
            amount REAL,
            total_odds REAL,
            potential_return REAL,
            result TEXT DEFAULT 'pending',
            actual_return REAL DEFAULT 0,
            profit REAL DEFAULT 0,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS fund_log (
            id INTEGER PRIMARY KEY,
            date TEXT,
            type TEXT,
            amount REAL,
            balance_before REAL,
            balance_after REAL,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS strategy_config (
            id INTEGER PRIMARY KEY,
            key TEXT UNIQUE,
            value REAL
        );
    """)
    conn.commit()
    conn.close()


def query(sql, params=()):
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def execute(sql, params=()):
    conn = get_db()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def query_one(sql, params=()):
    conn = get_db()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return dict(row) if row else None
