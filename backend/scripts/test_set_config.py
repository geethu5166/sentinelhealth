import asyncio
import asyncpg
import uuid

async def test():
    conn = await asyncpg.connect(
        host="localhost",
        port=5433,
        database="sentinelhealth",
        user="sentinel_app",
        password="sentinel_app_pass_2024"
    )
    t_id = "11111111-1111-1111-1111-111111111111"
    async with conn.transaction():
        await conn.execute("SELECT set_config('app.current_tenant_id', $1, true);", t_id)
        val = await conn.fetchval("SELECT current_setting('app.current_tenant_id', true);")
        print("Set local result:", val)
        alerts = await conn.fetch("SELECT id, tenant_id FROM alerts;")
        print("Alerts found:", len(alerts))
    
    val2 = await conn.fetchval("SELECT current_setting('app.current_tenant_id', true);")
    print("After tx:", val2)
    await conn.close()

asyncio.run(test())

