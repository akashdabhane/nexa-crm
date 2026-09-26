"""Read-only aggregate queries for the dashboard and reports.

Everything is a plain SQL GROUP BY — no reporting engine, no caching.
Date filters are inclusive calendar days (start_date 00:00 to end_date 23:59).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import ColumnElement, and_, case, func, select, true
from sqlalchemy.orm import Session

from app.models import Activity, Company, Contact, Deal, Lead, PipelineStage, Profile
from app.models.enums import DealStatus, LeadStatus, StageType
from app.services.pipelines import get_default_pipeline


@dataclass
class DateRange:
    start: date | None = None
    end: date | None = None

    def filter(self, column) -> ColumnElement[bool]:
        conditions = []
        if self.start:
            conditions.append(column >= datetime.combine(self.start, time.min, tzinfo=UTC))
        if self.end:
            conditions.append(column < datetime.combine(self.end + timedelta(days=1), time.min, tzinfo=UTC))
        return and_(*conditions) if conditions else true()


def _rate(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def _month(column):
    return func.to_char(func.date_trunc("month", column), "YYYY-MM")


def lead_conversion(db: Session, period: DateRange) -> dict:
    in_period = period.filter(Lead.created_at)
    by_status = dict(db.execute(select(Lead.status, func.count()).where(in_period).group_by(Lead.status)).all())
    total = sum(by_status.values())
    converted = by_status.get(LeadStatus.CONVERTED, 0)
    avg_days = db.scalar(
        select(func.avg(func.extract("epoch", Lead.converted_at - Lead.created_at) / 86400)).where(
            in_period, Lead.converted_at.is_not(None)
        )
    )
    return {
        "total_leads": total,
        "converted": converted,
        "conversion_rate": _rate(converted, total),
        "avg_days_to_convert": round(float(avg_days), 1) if avg_days is not None else None,
        "by_status": [{"status": status, "count": by_status.get(status, 0)} for status in LeadStatus],
    }


def pipeline(db: Session, period: DateRange) -> list[dict]:
    """Open deals per stage of the default pipeline (count, value, weighted value)."""
    default_pipeline = get_default_pipeline(db)
    rows = db.execute(
        select(
            PipelineStage.id,
            PipelineStage.name,
            PipelineStage.position,
            func.count(Deal.id),
            func.coalesce(func.sum(Deal.value), 0),
            func.coalesce(func.sum(Deal.value * Deal.probability / 100), 0),
        )
        .join(Deal, and_(Deal.stage_id == PipelineStage.id, period.filter(Deal.created_at)), isouter=True)
        .where(PipelineStage.pipeline_id == default_pipeline.id, PipelineStage.stage_type == StageType.OPEN)
        .group_by(PipelineStage.id)
        .order_by(PipelineStage.position)
    ).all()
    return [
        {"stage_id": r[0], "stage": r[1], "count": r[3], "value": float(r[4]), "weighted_value": float(r[5])}
        for r in rows
    ]


def revenue_by_month(db: Session, period: DateRange) -> list[dict]:
    month = _month(Deal.closed_at)
    rows = db.execute(
        select(month, func.count(), func.sum(Deal.value))
        .where(Deal.status == DealStatus.WON, period.filter(Deal.closed_at))
        .group_by(month)
        .order_by(month)
    ).all()
    return [{"month": m, "deals": count, "revenue": float(total or 0)} for m, count, total in rows]


def win_loss(db: Session, period: DateRange) -> dict:
    month = _month(Deal.closed_at)
    is_won = Deal.status == DealStatus.WON
    is_lost = Deal.status == DealStatus.LOST
    closed = Deal.status.in_([DealStatus.WON, DealStatus.LOST])
    rows = db.execute(
        select(
            month,
            func.count().filter(is_won),
            func.count().filter(is_lost),
            func.coalesce(func.sum(Deal.value).filter(is_won), 0),
            func.coalesce(func.sum(Deal.value).filter(is_lost), 0),
        )
        .where(closed, period.filter(Deal.closed_at))
        .group_by(month)
        .order_by(month)
    ).all()
    by_month = [
        {"month": m, "won": w, "lost": lo, "won_value": float(wv), "lost_value": float(lv)}
        for m, w, lo, wv, lv in rows
    ]
    won = sum(row["won"] for row in by_month)
    lost = sum(row["lost"] for row in by_month)
    return {
        "won": won,
        "lost": lost,
        "won_value": sum(row["won_value"] for row in by_month),
        "lost_value": sum(row["lost_value"] for row in by_month),
        "win_rate": _rate(won, won + lost),
        "by_month": by_month,
    }


def rep_performance(db: Session, period: DateRange) -> list[dict]:
    """One row per active user. Closed-deal metrics use closed_at; others use created_at."""
    closed_in_period = period.filter(Deal.closed_at)

    def per_owner(stmt):
        return {owner_id: values for owner_id, *values in db.execute(stmt).all()}

    deals = per_owner(
        select(
            Deal.owner_id,
            func.count().filter(Deal.status == DealStatus.WON, closed_in_period),
            func.coalesce(func.sum(Deal.value).filter(Deal.status == DealStatus.WON, closed_in_period), 0),
            func.count().filter(Deal.status == DealStatus.LOST, closed_in_period),
            func.count().filter(Deal.status == DealStatus.OPEN),
            func.coalesce(func.sum(Deal.value).filter(Deal.status == DealStatus.OPEN), 0),
        ).group_by(Deal.owner_id)
    )
    leads = per_owner(
        select(
            Lead.owner_id,
            func.count().filter(period.filter(Lead.created_at)),
            func.count().filter(Lead.status == LeadStatus.CONVERTED, period.filter(Lead.converted_at)),
        ).group_by(Lead.owner_id)
    )
    activities = per_owner(
        select(Activity.owner_id, func.count()).where(period.filter(Activity.occurred_at)).group_by(Activity.owner_id)
    )

    result = []
    for user in db.scalars(select(Profile).where(Profile.is_active.is_(True)).order_by(Profile.full_name)):
        won, won_value, lost, open_count, open_value = deals.get(user.id, (0, 0, 0, 0, 0))
        new_leads, converted = leads.get(user.id, (0, 0))
        result.append(
            {
                "user_id": user.id,
                "name": user.full_name,
                "role": user.role,
                "deals_won": won,
                "revenue": float(won_value),
                "deals_lost": lost,
                "win_rate": _rate(won, won + lost),
                "open_deals": open_count,
                "open_value": float(open_value),
                "leads": new_leads,
                "leads_converted": converted,
                "activities": activities.get(user.id, (0,))[0],
            }
        )
    result.sort(key=lambda row: row["revenue"], reverse=True)
    return result


def lead_sources(db: Session, period: DateRange) -> list[dict]:
    converted = func.count().filter(Lead.status == LeadStatus.CONVERTED)
    rows = db.execute(
        select(Lead.source, func.count(), converted, func.avg(Lead.score))
        .where(period.filter(Lead.created_at))
        .group_by(Lead.source)
    ).all()
    stats = {source: (total, conv, avg) for source, total, conv, avg in rows}
    result = []
    for source, (total, conv, avg) in sorted(stats.items(), key=lambda item: item[1][0], reverse=True):
        result.append(
            {
                "source": source,
                "leads": total,
                "converted": conv,
                "conversion_rate": _rate(conv, total),
                "avg_score": round(float(avg), 1) if avg is not None else 0,
            }
        )
    return result


def dashboard_summary(db: Session) -> dict:
    deal_stats = db.execute(
        select(
            func.count().filter(Deal.status == DealStatus.OPEN),
            func.count().filter(Deal.status == DealStatus.WON),
            func.count().filter(Deal.status == DealStatus.LOST),
            func.coalesce(func.sum(Deal.value).filter(Deal.status == DealStatus.OPEN), 0),
            func.coalesce(func.sum(Deal.value).filter(Deal.status == DealStatus.WON), 0),
            func.coalesce(func.sum(Deal.value * Deal.probability / 100).filter(Deal.status == DealStatus.OPEN), 0),
        )
    ).one()
    open_leads = case((Lead.status.in_([LeadStatus.CONVERTED, LeadStatus.UNQUALIFIED]), 0), else_=1)
    lead_total, lead_open, lead_converted = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(open_leads), 0),
            func.count().filter(Lead.status == LeadStatus.CONVERTED),
        )
    ).one()
    won, lost = deal_stats[1], deal_stats[2]
    return {
        "contacts": db.scalar(select(func.count()).select_from(Contact)),
        "companies": db.scalar(select(func.count()).select_from(Company)),
        "leads": lead_total,
        "open_leads": int(lead_open),
        "active_deals": deal_stats[0],
        "won_deals": won,
        "lost_deals": lost,
        "pipeline_value": float(deal_stats[3]),
        "won_value": float(deal_stats[4]),
        "weighted_pipeline_value": float(deal_stats[5]),
        "win_rate": _rate(won, won + lost),
        "lead_conversion_rate": _rate(lead_converted, lead_total),
        "converted_leads": lead_converted,
    }
