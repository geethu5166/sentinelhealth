import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host="localhost",
        port=5433,
        database="sentinelhealth",
        user="sentinel_migrator",
        password="sentinel_migrator_pass_2024"
    )
    for table in ["alerts", "data_sources", "preventive_tasks", "signal_records", "geographies"]:
        print(f"=== {table} ===")
        rows = await conn.fetch(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns WHERE table_name = $1 ORDER BY ordinal_position",
            table
        )
        for r in rows:
            print(f"  {r['column_name']} ({r['data_type']}, nullable={r['is_nullable']}, default={r['column_default']})")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check())

