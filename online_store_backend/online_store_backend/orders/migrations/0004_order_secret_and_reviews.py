import secrets
import string

import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models
from django.db.models import Q

import online_store_backend.orders.models


def _random_token(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def backfill_order_secret_and_review_tokens(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    OrderItem = apps.get_model("orders", "OrderItem")

    for order in Order.objects.filter(Q(order_secret__isnull=True) | Q(order_secret="")).iterator():
        order.order_secret = _random_token(12)
        order.save(update_fields=["order_secret"])

    used_tokens = set(
        OrderItem.objects.exclude(review_token__isnull=True)
        .exclude(review_token="")
        .values_list("review_token", flat=True)
    )
    for item in OrderItem.objects.filter(Q(review_token__isnull=True) | Q(review_token="")).iterator():
        token = _random_token(24)
        while token in used_tokens:
            token = _random_token(24)
        used_tokens.add(token)
        item.review_token = token
        item.save(update_fields=["review_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0003_orderitem_discount_snapshot"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="order_secret",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="review_left_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="review_token",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_id", models.CharField(max_length=255)),
                ("rating", models.PositiveSmallIntegerField()),
                ("pros", models.TextField(blank=True)),
                ("cons", models.TextField(blank=True)),
                ("comment", models.TextField(blank=True)),
                ("is_anonymous", models.BooleanField(default=False)),
                ("author_display_name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.RunPython(backfill_order_secret_and_review_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="order_secret",
            field=models.CharField(default=online_store_backend.orders.models.generate_order_secret, max_length=32),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="review_token",
            field=models.CharField(default=online_store_backend.orders.models.generate_review_token, max_length=64, unique=True),
        ),
        migrations.AddIndex(
            model_name="review",
            index=models.Index(fields=["product_id", "created_at"], name="orders_revi_product_7bb53c_idx"),
        ),
        migrations.AddIndex(
            model_name="review",
            index=models.Index(fields=["order"], name="orders_revi_order_i_329eec_idx"),
        ),
    ]
