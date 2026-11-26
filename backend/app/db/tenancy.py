"""Organization (tenant) isolation, enforced on the database session.

Every CRM table has an `organization_id` column (`OrgScopedMixin`). Once a
request's organization is known, `set_current_org(db, org_id)` stores it on the
session, and two session events do the rest:

- every SELECT / UPDATE / DELETE run through the session is limited to the
  current organization, for each org-scoped table it reads, including joins,
  counts and aggregates, relationship loads and `db.get()`;
- every new org-scoped row gets `organization_id` filled in on flush (or, if the
  session switches to another organization first, at the switch).

Two mechanisms work together, because neither covers everything alone:

1. `with_loader_criteria`: the main one. It covers statements with an entity or
   entity attribute in the select list, explicit select_from()/joins (putting
   the condition in the ON clause of outer joins), and the queries the ORM
   builds later: relationship loads, refreshes, `db.get()`, entity subqueries.
2. An explicit `WHERE <table>.organization_id = :org` for the one shape the
   loader criteria silently skip: a select list of only functions/aggregates,
   such as `select(func.count().filter(Deal.status == "open"))`, where the table
   is implied by columns inside a function. (This once leaked one
   organization's dashboard deal totals into another's.)

It fails closed: with no organization set, queries match nothing and inserts
raise. System code that must look across organizations (e.g. finding which
organization owns an incoming webhook) opts out per statement with
`.execution_options(all_orgs=True)`.

Limitation: a subquery whose select list is only aggregates/functions (no entity)
is not reached by either mechanism; write those with `.select_from(Model)`.
"""

import uuid
from collections.abc import Iterator

from sqlalchemy import Alias, ForeignKey, Join, TableClause, event
from sqlalchemy.orm import Mapped, ORMExecuteState, Session, mapped_column, with_loader_criteria
from sqlalchemy.sql.expression import FromClause

# Matches no row: used when no organization is selected, so a forgotten scope returns nothing.
NO_ORG = uuid.UUID(int=0)
ORG_KEY = "org_id"


class OrgScopedMixin:
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )


class NoOrganizationError(RuntimeError):
    """An org-scoped row was created while no organization was selected (a bug, not user error)."""


def set_current_org(db: Session, org_id: uuid.UUID | None) -> None:
    previous = db.info.get(ORG_KEY)
    if previous is not None and previous != org_id:
        # Rows added while the previous organization was selected belong to it, even if they're flushed later
        # (e.g. the Meta webhook works through several organizations in one session).
        _stamp_pending(db, previous)
    if org_id is None:
        db.info.pop(ORG_KEY, None)
    else:
        db.info[ORG_KEY] = org_id


def current_org(db: Session) -> uuid.UUID | None:
    return db.info.get(ORG_KEY)


def _tenant_table_names() -> frozenset[str]:
    from app.db.base import Base

    return frozenset(
        mapper.local_table.name for mapper in Base.registry.mappers if issubclass(mapper.class_, OrgScopedMixin)
    )


def _org_scoped_froms(from_clause: FromClause, tenant_tables: frozenset[str]) -> Iterator[FromClause]:
    """Org-scoped tables (or aliases of them) in one FROM element, looking inside joins."""
    if isinstance(from_clause, Join):
        yield from _org_scoped_froms(from_clause.left, tenant_tables)
        yield from _org_scoped_froms(from_clause.right, tenant_tables)
        return
    table = from_clause.element if isinstance(from_clause, Alias) else from_clause
    if isinstance(table, TableClause) and table.name in tenant_tables:
        yield from_clause


def _froms_missed_by_loader_criteria(statement) -> list[FromClause]:
    """FROM elements of a SELECT that `with_loader_criteria` would leave unfiltered.

    The loader criteria cover any statement with an entity or entity attribute in its select
    list, or any explicit select_from()/join(), and put the condition in the right place (the
    ON clause for outer joins). They miss one shape: a select list made only of functions and
    aggregates, with the tables implied by the columns inside them. Only then is an explicit
    WHERE added; with no joins in that shape, a WHERE is exactly equivalent.
    """
    if any(desc.get("entity") is not None for desc in statement.column_descriptions):
        return []
    froms = statement.get_final_froms()
    if any(isinstance(from_, Join) for from_ in froms):
        return []
    return list(froms)


@event.listens_for(Session, "do_orm_execute")
def _scope_statement(state: ORMExecuteState) -> None:
    if not (state.is_select or state.is_update or state.is_delete):
        return
    # Relationship and refresh loads inherit the criteria from the statement that loaded the parent.
    if state.is_column_load or state.is_relationship_load:
        return
    if state.execution_options.get("all_orgs", False):
        return
    org_id = state.session.info.get(ORG_KEY) or NO_ORG
    tenant_tables = _tenant_table_names()
    statement = state.statement

    if state.is_select:
        froms = _froms_missed_by_loader_criteria(statement)
    else:  # UPDATE / DELETE
        froms = [statement.table]
    conditions = [
        table.c.organization_id == org_id for from_ in froms for table in _org_scoped_froms(from_, tenant_tables)
    ]
    if conditions:
        statement = statement.where(*conditions)

    state.statement = statement.options(
        with_loader_criteria(OrgScopedMixin, lambda cls: cls.organization_id == org_id, include_aliases=True)
    )


def _stamp_pending(session: Session, org_id: uuid.UUID) -> None:
    for obj in session.new:
        if isinstance(obj, OrgScopedMixin) and obj.organization_id is None:
            obj.organization_id = org_id


@event.listens_for(Session, "before_flush")
def _stamp_new_rows(session: Session, _flush_context, _instances) -> None:
    org_id = session.info.get(ORG_KEY)
    if org_id is None:
        for obj in session.new:
            if isinstance(obj, OrgScopedMixin) and obj.organization_id is None:
                raise NoOrganizationError(f"No organization selected for new {type(obj).__name__}")
        return
    _stamp_pending(session, org_id)
