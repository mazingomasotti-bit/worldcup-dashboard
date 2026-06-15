# 资金管理服务

from datetime import datetime
from backend.database import query, query_one, execute
from backend.config import DEFAULT_PRINCIPAL, DEFAULT_BET_RATIO


def get_current_balance():
    logs = query("SELECT balance_after FROM fund_log ORDER BY id DESC LIMIT 1")
    if logs:
        return logs[0]["balance_after"]
    # 首次使用，初始化本金
    execute(
        "INSERT INTO fund_log (date, type, amount, balance_before, balance_after, note) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d"), "deposit", DEFAULT_PRINCIPAL, 0, DEFAULT_PRINCIPAL, "初始本金")
    )
    return DEFAULT_PRINCIPAL


def get_config(key):
    row = query_one("SELECT value FROM strategy_config WHERE key=?", (key,))
    return row["value"] if row else None


def check_bet_limit(amount):
    balance = get_current_balance()
    ratio = get_config("bet_ratio") or DEFAULT_BET_RATIO
    max_allowed = round(balance * ratio, 2)
    weekly_limit = int(get_config("weekly_limit") or 3)

    week_count = query(
        "SELECT COUNT(*) as cnt FROM bets WHERE created_at >= date('now', 'weekday 0', '-7 days')"
    )[0]["cnt"]

    if week_count >= weekly_limit:
        return {"blocked": True, "reason": f"本周已达{weekly_limit}次投注上限", "max_bet": max_allowed}
    if amount > max_allowed:
        return {"blocked": True, "reason": f"超过单次投注上限 ¥{max_allowed}（{ratio*100:.0f}%规则）", "max_bet": max_allowed}
    return {"blocked": False, "max_bet": max_allowed}


def record_bet(bet_id, amount, note):
    balance = get_current_balance()
    new_balance = round(balance - amount, 2)
    execute(
        "INSERT INTO fund_log (date, type, amount, balance_before, balance_after, note) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d"), "bet", -amount, balance, new_balance, f"投注#{bet_id}: {note}")
    )


def settle_bet(bet_id, profit, matches_info):
    balance = get_current_balance()
    # 投注金额已扣除，结算时只需要加回actual_return
    bet = query_one("SELECT amount, actual_return FROM bets WHERE id=?", (bet_id,))
    if not bet:
        return
    actual_return = bet["actual_return"]
    if actual_return > 0:
        new_balance = round(balance + actual_return, 2)
        note = f"结算#{bet_id}: 盈利¥{profit}"
        t = "profit" if profit > 0 else "loss"
    else:
        new_balance = balance
        note = f"结算#{bet_id}: 未中奖"
        t = "loss"

    execute(
        "INSERT INTO fund_log (date, type, amount, balance_before, balance_after, note) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d"), t, actual_return, balance, new_balance, note)
    )
