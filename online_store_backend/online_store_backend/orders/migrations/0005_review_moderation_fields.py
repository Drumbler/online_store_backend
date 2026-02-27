import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0004_order_secret_and_reviews"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="is_published",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="review",
            name="moderated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="review",
            name="moderated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="moderated_reviews",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
