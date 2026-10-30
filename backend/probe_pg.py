import asyncio
import sys
sys.path.insert(0, ".")
from tests.postgres.test_rls_postgres import check_postgres_availability
print(asyncio.run(check_postgres_availability()))

