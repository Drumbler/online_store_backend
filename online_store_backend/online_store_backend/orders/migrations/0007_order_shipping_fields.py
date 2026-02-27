from decimal import Decimal

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0006_order_pending_payment_and_payments"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="shipping_provider",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_type",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_price",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_address",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="pickup_point_id",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
