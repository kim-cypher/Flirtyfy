from django.db import migrations


class Migration(migrations.Migration):
    """
    Creates the pgvector extension as a real migration step, not a runner hook.

    The previous approach (accounts.test_runner.PGVectorTestRunner) tried to
    enable the extension via a Python hook around setup_databases(), but
    Django's test-database creation runs migrations as part of the same call
    that creates the database — there is no window between "database exists"
    and "migrations start" for a runner to inject SQL into. The extension
    call landed on the original (dev) connection instead, so a fresh test
    database never had the extension and 0003_novelty_models' vector column
    failed every time. A migration runs at the correct point in the sequence
    regardless of which database (dev or test) is being built.
    """

    dependencies = [
        ('accounts', '0002_userprofile_age_userprofile_age_verified_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        ),
    ]
