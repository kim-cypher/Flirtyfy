from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_remove_aireply_accounts_ai_embeddi_f2f41e_idx'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE auth_user ADD CONSTRAINT auth_user_email_unique UNIQUE (email);",
            reverse_sql="ALTER TABLE auth_user DROP CONSTRAINT auth_user_email_unique;",
        ),
    ]
