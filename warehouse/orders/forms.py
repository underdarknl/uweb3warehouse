from wtforms import (
    Form,
    IntegerField,
    SelectField,
    StringField,
    validators,
    FieldList,
    FormField,
)

from warehouse.common.helpers import BaseForm


class OrderProduct(BaseForm):
    product_sku = StringField("product_sku", validators=[validators.InputRequired()])
    quantity = IntegerField("quantity", validators=[validators.NumberRange(min=1, max=65535)])
    description = StringField(
        "description", validators=[validators.Optional(), validators.Length(max=255)]
    )


class CreateOrderForm(BaseForm):
    description = StringField("description", validators=[validators.InputRequired()])
    status = SelectField(
        "status",
        choices=[
            ("new", "new"),
            ("reservation", "reservation"),
            ("completed", "completed"),
            ("canceled", "canceled")
        ],
    )
    products = FieldList(FormField(OrderProduct), min_entries=1)
