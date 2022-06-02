from wtforms import (
    DecimalField,
    Form,
    IntegerField,
    StringField,
    TextAreaField,
    validators,
)


class ProductForm(Form):
    sku = StringField("sku", [validators.Length(min=1, max=45)])
    name = StringField(
        "name", [validators.Length(min=5, max=255), validators.DataRequired()]
    )
    ean = StringField("ean", [validators.Length(min=1, max=13), validators.Optional()])
    gs1 = IntegerField(
        "gs1", [validators.NumberRange(min=1, max=32767), validators.Optional()]
    )
    description = TextAreaField("description", validators=[validators.Optional()])
    assemblycosts = DecimalField(
        "assemblycosts", validators=[validators.DataRequired()]
    )


class ProductAssembleForm(Form):
    part = StringField("part", [validators.Length(min=1, max=45)])
    amount = IntegerField("amount", [validators.NumberRange(min=1, max=65535)])
    assemblycosts = DecimalField(
        "assemblycosts", validators=[validators.DataRequired()]
    )
