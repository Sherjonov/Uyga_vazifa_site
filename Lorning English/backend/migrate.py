"""Eski ma'lumotlar bazasiga yangi ustunlarni avtomatik qo'shadi (aedu.db ni o'chirib yubormasdan)."""
from sqlalchemy import inspect, text


def _default_sql(col, dialect):
    sd = col.server_default
    arg = getattr(sd, "arg", None)
    if arg is None:
        return None
    if isinstance(arg, str):
        return "'" + arg.replace("'", "''") + "'"
    try:
        return str(arg.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))
    except Exception:
        return None


def ensure_schema(engine, base) -> None:
    """Yetishmayotgan jadvallarni yaratadi va eski jadvallarga yangi ustunlarni qo'shadi.
    Masofaviy bazada tez ishlashi uchun jadval va ustunlar bir necha so'rov bilan o'qiladi."""
    existing = set(inspect(engine).get_table_names())
    missing = [t for t in base.metadata.sorted_tables if t.name not in existing]
    if missing:
        base.metadata.create_all(bind=engine, tables=missing, checkfirst=False)
        existing |= {t.name for t in missing}
    run(engine, base, existing, background=True)


def run(engine, base, existing_tables=None, background: bool = False) -> None:
    insp = inspect(engine)
    existing = set(existing_tables) if existing_tables is not None else set(insp.get_table_names())
    if engine.dialect.name == "mysql":  # bitta so'rov (get_multi_columns masofaviy bazada juda sekin)
        columns: dict = {}
        with engine.connect() as conn:
            for table_name, column_name in conn.execute(text(
                    "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = DATABASE()")):
                columns.setdefault(table_name, []).append({"name": column_name})
    else:
        columns = {name: cols for (_, name), cols in insp.get_multi_columns().items()}
    quote = engine.dialect.identifier_preparer.quote
    with engine.begin() as conn:
        for table in base.metadata.sorted_tables:
            if table.name not in existing:
                continue  # yangi jadvalni create_all yaratadi
            have = {c["name"] for c in columns.get(table.name, [])}
            for col in table.columns:
                if col.name in have:
                    continue
                ddl = f"ALTER TABLE {quote(table.name)} ADD COLUMN {quote(col.name)} {col.type.compile(dialect=engine.dialect)}"
                default = _default_sql(col, engine.dialect)
                if default is not None:
                    ddl += f" DEFAULT {default}"
                conn.execute(text(ddl))
                print(f"[migrate] {table.name}.{col.name} ustuni qo'shildi")
    if not background:
        _data_fixes(engine, existing)
    else:  # masofaviy bazada server tezroq ochilishi uchun ma'lumotlarni tuzatish fonda bajariladi
        import threading
        threading.Thread(target=_data_fixes, args=(engine, existing), daemon=True).start()


def _data_fixes(engine, existing: set) -> None:
    try:
        with engine.begin() as conn:
            _normalize_tracks(conn, existing)
            _normalize_penalty(conn, existing)
            _migrate_role_profiles(conn, existing)
            _drop_legacy_user_score(conn)
    except Exception as error:  # noqa: BLE001
        print(f"[migrate] ma'lumotlarni tuzatishda xato: {error}")


def _migrate_role_profiles(conn, existing: set[str]) -> None:
    if not {"users", "students", "teachers", "subscriptions"}.issubset(existing):
        return
    user_columns = {c["name"] for c in inspect(conn).get_columns("users")}
    profiles = (
        ("students", "student", "user_id", (("claimed", "1"), ("total_score", "0"))),
        ("teachers", "teacher", "user_id", ()),
        ("subscriptions", "teacher", "teacher_id", (
            ("subscription_until", "NULL"),
            ("trial_used", "0"),
            ("has_paid", "0"),
            ("fake_receipt_warning", "0"),
        )),
    )
    for table, role, key_column, fields in profiles:
        names = [key_column]
        expressions = ["u.id"]
        for field, fallback in fields:
            names.append(field)
            source = f"u.{field}" if field in user_columns else fallback
            expressions.append(f"COALESCE({source}, {fallback})")
        columns_sql = ", ".join(names)
        values_sql = ", ".join(expressions)
        conn.execute(text(
            f"INSERT INTO {table} ({columns_sql}) "
            f"SELECT {values_sql} FROM users AS u "
            f"WHERE u.role = :role AND NOT EXISTS "
            f"(SELECT 1 FROM {table} AS p WHERE p.{key_column} = u.id)"
        ), {"role": role})


def _drop_legacy_user_score(conn) -> None:
    """Drop the old required users.total_score column after its values are copied to students."""
    inspector = inspect(conn)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "total_score" not in columns:
        return

    quote = conn.dialect.identifier_preparer.quote
    for index in inspector.get_indexes("users"):
        if "total_score" in (index.get("column_names") or []):
            conn.execute(text(f"DROP INDEX {quote(index['name'])}"))

    if conn.dialect.name == "sqlite":
        version = conn.dialect.server_version_info
        if version and version < (3, 35, 0):
            raise RuntimeError("SQLite 3.35 or later is required to remove the obsolete users.total_score column.")
    conn.execute(text(f"ALTER TABLE users DROP COLUMN {quote('total_score')}"))
    print("[migrate] eski users.total_score ustuni olib tashlandi")


def _normalize_tracks(conn, existing: set[str]) -> None:
    """Maktab/universitet/to'garak yo'nalishlari olib tashlandi: hammasi "english" bo'ladi."""
    if "users" in existing:
        conn.execute(text("UPDATE users SET track = 'english' WHERE track IN ('school', 'university', 'circle')"))
    if "groups" in existing:
        conn.execute(text(f"UPDATE {conn.dialect.identifier_preparer.quote('groups')} SET kind = 'english' WHERE kind IN ('school', 'university', 'circle')"))


def _normalize_penalty(conn, existing: set[str]) -> None:
    """Eski standart "Kelmadi: -20" yangi qoidaga (-5) o'tkaziladi (o'qituvchi Sozlamalarda o'zgartira oladi)."""
    if "teacher_settings" in existing:
        conn.execute(text("UPDATE teacher_settings SET absence_penalty = 5 WHERE absence_penalty = 20"))
