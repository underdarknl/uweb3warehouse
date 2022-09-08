from wtforms import (
    DecimalField,
    Form,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
    ValidationError,
    validators,
    FieldList,
    FormField,
)


class OrderProduct(Form):
    product_sku = StringField("product_sku", validators=[validators.InputRequired()])
    quantity = IntegerField("quantity", validators=[validators.NumberRange(min=1)])
    description = StringField(
        "description", validators=[validators.Optional(), validators.Length(max=255)]
    )


class CreateOrderForm(Form):
    description = StringField("description", validators=[validators.InputRequired()])
    status = SelectField(
        "status",
        choices=[
            ("new", "new"),
            ("reservation", "reservation"),
            ("completed", "completed"),
        ],
    )
    products = FieldList(FormField(OrderProduct), min_entries=1)
