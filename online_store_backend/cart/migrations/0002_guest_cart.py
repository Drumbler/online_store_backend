import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="cart",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="cart",
            name="session_key",
            field=models.CharField(blank=True, db_index=True, max_length=40, null=True),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="currency_snapshot",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="image_url_snapshot",
            field=models.URLField(blank=True, max_length=1000),
        ),
        migrations.RemoveConstraint(
            model_name="cart",
            name="unique_active_cart_per_user",
        ),
        migrations.AddConstraint(
            model_name="cart",
            constraint=models.UniqueConstraint(
                condition=Q(("status", "active"), ("user__isnull", False)),
                fields=("user",),
                name="unique_active_cart_per_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="cart",
            constraint=models.UniqueConstraint(
                condition=Q(("status", "active"), ("session_key__isnull", False)),
                fields=("session_key",),
                name="unique_active_cart_per_session",
            ),
        ),
    ]
