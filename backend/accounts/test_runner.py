"""
Custom Django test runner that enables pgvector for test database setup
"""

from django.test.runner import DiscoverRunner
from django.db import connection, DEFAULT_DB_ALIAS


class PGVectorTestRunner(DiscoverRunner):
    """Test runner that enables pgvector extension in test database"""

    def setup_databases(self, **kwargs):
        """Setup databases and enable pgvector extension"""
        # First, temporarily enable pgvector in the default database to allow creation
        self._enable_pgvector_in_db(DEFAULT_DB_ALIAS)
        
        # Now run the normal setup
        old_names = super().setup_databases(**kwargs)
        
        # Ensure pgvector is enabled in the test database too
        self._enable_pgvector_in_db(DEFAULT_DB_ALIAS)
        
        return old_names

    def _enable_pgvector_in_db(self, alias):
        """Enable pgvector extension in specified database"""
        try:
            db_conn = connection
            with db_conn.cursor() as cursor:
                cursor.execute('CREATE EXTENSION IF NOT EXISTS vector')
            self.stdout.write(self.style.SUCCESS('✓ pgvector extension enabled'))
        except Exception as e:
            # Extension might already exist, that's ok
            pass