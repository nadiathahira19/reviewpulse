from app.models import Base


def test_all_tables_exist() -> None:
    assert set(Base.metadata.tables) == {
        "tenants",
        "users",
        "api_keys",
        "review_batches",
        "reviews",
        "predictions",
    }


def test_every_table_except_tenants_has_tenant_id() -> None:
    for name, table in Base.metadata.tables.items():
        if name != "tenants":
            assert "tenant_id" in table.columns, name
