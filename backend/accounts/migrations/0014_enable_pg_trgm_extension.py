from django.db import migrations


class Migration(migrations.Migration):
    """
    Enables Postgres trigram similarity for the dedup layer
    (accounts/services/dedup.py::dedupe_similar), replacing the
    OpenAI-embedding semantic check.

    The GIN index makes TrigramSimilarity('normalized_text', <candidate>)
    lookups fast over each user's 30-day reply history.
    """

    dependencies = [
        ('accounts', '0013_usercredits_payment_notification_creditgrant'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS accounts_aireply_normtext_trgm_idx "
                "ON accounts_aireply USING gin (normalized_text gin_trgm_ops);"
            ),
            reverse_sql="DROP INDEX IF EXISTS accounts_aireply_normtext_trgm_idx;",
        ),
    ]
