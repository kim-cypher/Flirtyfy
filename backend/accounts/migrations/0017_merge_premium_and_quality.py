from django.db import migrations


class Migration(migrations.Migration):
    """
    Merge migration — the rebase produced two migrations numbered 0014 that
    both branch off 0013:

      * 0014_enable_pg_trgm_extension  -> 0015_aireply_monitoring_fields
                                       -> 0016_aireply_quality_fields   (dedup/quality branch)
      * 0014_premiumemail_usercredits_is_premium                        (premium branch)

    They touch entirely different tables (pg_trgm + AIReply fields vs.
    PremiumEmail model + UserCredits.is_premium), so there is no operation
    conflict — only a graph conflict (two leaf nodes). This no-op migration
    unifies both leaves so `migrate` has a single head again.
    """

    dependencies = [
        ('accounts', '0016_aireply_quality_fields'),
        ('accounts', '0014_premiumemail_usercredits_is_premium'),
    ]

    operations = []
