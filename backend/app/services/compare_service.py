from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EquitySnapshot, Fill, JournalEvent, JournalEventType, Order, OrderSide, Run


async def equity_curve(session: AsyncSession, run_id: int) -> list[dict]:
    run = await session.get(Run, run_id)
    if not run:
        return []
    snaps = await session.execute(
        select(EquitySnapshot)
        .where(EquitySnapshot.run_id == run_id)
        .order_by(EquitySnapshot.recorded_at)
    )
    points = [
        {"t": s.recorded_at.isoformat(), "equity": s.equity, "mark_price": s.mark_price}
        for s in snaps.scalars()
    ]
    if not points:
        points.append(
            {
                "t": run.started_at.isoformat(),
                "equity": run.starting_equity,
                "mark_price": 0,
            }
        )
    return points


async def regime_summary(session: AsyncSession, run_id: int) -> dict[str, int]:
    result = await session.execute(
        select(JournalEvent).where(
            JournalEvent.run_id == run_id,
            JournalEvent.event_type == JournalEventType.regime_change,
        )
    )
    counts: dict[str, int] = {}
    for ev in result.scalars():
        label = ev.payload.get("regime")
        if not label:
            snap = ev.payload.get("regime_snapshot") or {}
            label = snap.get("label")
        label = label or "neutral"
        counts[label] = counts.get(label, 0) + 1
    return counts


async def compute_run_metrics(session: AsyncSession, run: Run) -> dict[str, Any]:
    fills = (
        await session.execute(select(Fill).where(Fill.run_id == run.id))
    ).scalars().all()
    orders = (
        await session.execute(select(Order).where(Order.run_id == run.id))
    ).scalars().all()

    sell_fills = []
    buy_fills = []
    for f in fills:
        order = next((o for o in orders if o.id == f.order_id), None)
        if not order:
            continue
        if order.side == OrderSide.sell:
            sell_fills.append(f)
        else:
            buy_fills.append(f)

    trade_count = len(sell_fills)
    wins = 0
    losses = 0
    win_sum = 0.0
    loss_sum = 0.0
    for i, sf in enumerate(sell_fills):
        bf = buy_fills[i] if i < len(buy_fills) else None
        if not bf:
            continue
        pnl = (sf.price - bf.price) * sf.qty - sf.fee - bf.fee
        if pnl >= 0:
            wins += 1
            win_sum += pnl
        else:
            losses += 1
            loss_sum += abs(pnl)

    win_rate = (wins / trade_count * 100) if trade_count else 0.0
    profit_factor = (win_sum / loss_sum) if loss_sum > 0 else None
    curve = await equity_curve(session, run.id)
    equities = [p["equity"] for p in curve]
    max_dd = 0.0
    peak = run.starting_equity
    for eq in equities:
        peak = max(peak, eq)
        if peak > 0:
            dd = (peak - eq) / peak * 100
            max_dd = max(max_dd, dd)
    final_equity = equities[-1] if equities else run.starting_equity
    return_pct = (
        (final_equity - run.starting_equity) / run.starting_equity * 100
        if run.starting_equity
        else 0.0
    )

    regime_counts = await regime_summary(session, run.id)
    dominant_regime = max(regime_counts, key=regime_counts.get) if regime_counts else None

    return {
        "run_id": run.id,
        "bot_id": run.bot_id,
        "template_id": run.template_id,
        "params": run.params_snapshot,
        "starting_equity": run.starting_equity,
        "final_equity": final_equity,
        "return_pct": return_pct,
        "trade_count": trade_count,
        "win_rate": win_rate,
        "max_drawdown_pct": max_dd,
        "profit_factor": profit_factor,
        "realized_pnl": run.realized_pnl,
        "regime_counts": regime_counts,
        "dominant_regime": dominant_regime,
    }


def build_insights(metrics: list[dict[str, Any]]) -> list[str]:
    if len(metrics) < 2:
        return ["Add at least two runs to compare."]
    insights: list[str] = []
    best = max(metrics, key=lambda m: m["return_pct"])
    worst = min(metrics, key=lambda m: m["return_pct"])
    insights.append(
        f"Run {best['run_id']} has the highest return ({best['return_pct']:.2f}%)."
    )
    if worst["run_id"] != best["run_id"]:
        insights.append(
            f"Run {worst['run_id']} has the lowest return ({worst['return_pct']:.2f}%)."
        )
    high_wr = max(metrics, key=lambda m: m["win_rate"])
    low_wr = min(metrics, key=lambda m: m["win_rate"])
    if high_wr["win_rate"] - low_wr["win_rate"] > 10:
        insights.append(
            f"Run {high_wr['run_id']} win rate is much higher, but check avg loss vs Run {low_wr['run_id']}."
        )
    dd = max(metrics, key=lambda m: m["max_drawdown_pct"])
    insights.append(
        f"Run {dd['run_id']} experienced the largest drawdown ({dd['max_drawdown_pct']:.2f}%)."
    )
    for m in metrics:
        dom = m.get("dominant_regime")
        counts = m.get("regime_counts") or {}
        if dom and counts:
            total = sum(counts.values())
            pct = counts.get(dom, 0) / total * 100 if total else 0
            insights.append(
                f"Run {m['run_id']} ({m['template_id']}) spent ~{pct:.0f}% of bars in '{dom}' regime."
            )
    return insights


def param_diff(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if len(metrics) < 2:
        return {}
    a, b = metrics[0], metrics[1]
    keys = set(a.get("params", {})) | set(b.get("params", {}))
    diff = {}
    for k in keys:
        va, vb = a.get("params", {}).get(k), b.get("params", {}).get(k)
        if va != vb:
            diff[k] = {"run_a": va, "run_b": vb}
    return diff


async def compare_runs(session: AsyncSession, run_ids: list[int]) -> dict[str, Any]:
    metrics = []
    series = []
    for rid in run_ids:
        run = await session.get(Run, rid)
        if not run:
            continue
        m = await compute_run_metrics(session, run)
        metrics.append(m)
        curve = await equity_curve(session, rid)
        base = run.starting_equity or 1.0
        series.append(
            {
                "run_id": rid,
                "label": f"Run {rid} ({run.template_id})",
                "points": [
                    {"t": p["t"], "normalized_pct": (p["equity"] - base) / base * 100}
                    for p in curve
                ],
            }
        )
    return {
        "metrics": metrics,
        "series": series,
        "insights": build_insights(metrics),
        "param_diff": param_diff(metrics),
    }
