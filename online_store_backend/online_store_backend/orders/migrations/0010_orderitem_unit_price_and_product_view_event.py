from decimal import Decimal

from django.db import migrations
from django.db import models


def copy_snapshot_price_to_unit_price(apps, schema_editor):
    OrderItem = apps.get_model("orders", "OrderItem")
    OrderItem.objects.filter(unit_price_snapshot__isnull=False).update(unit_price=models.F("unit_price_snapshot"))


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0009_order_paid_at_payment_completed_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.RunPython(copy_snapshot_price_to_unit_price, migrations.RunPython.noop),
        migrations.CreateModel(
            name="ProductViewEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_id", models.CharField(max_length=255)),
                ("viewed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-viewed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="productviewevent",
            index=models.Index(fields=["product_id", "viewed_at"], name="orders_pve_pid_viewed_idx"),
        ),
    ]
