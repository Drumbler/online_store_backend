from decimal import Decimal

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0002_guest_checkout"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="discount_percent",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="unit_price_final",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="unit_price_original",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
    ]
