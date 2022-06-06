from wtforms import (
    DecimalField,
    Form,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
    validators,
)


class ProductForm(Form):
    sku = StringField(
        "sku",
        [validators.Length(min=1, max=45)],
        description="""The name for each sku in your warehouse must be unique,
                      only products that can be ordered by end customers should have an easily recognizable sku.""",
    )
    name = StringField(
        "name",
        [validators.Length(min=5, max=255), validators.DataRequired()],
        description="The name of the product",
    )
    ean = StringField(
        "ean",
        [validators.Length(min=1, max=13), validators.Optional()],
        description="The ean barcode for each product or part in your warehouse must be unique.",
    )
    gs1 = IntegerField(
        "gs1",
        [validators.NumberRange(min=1, max=32767), validators.Optional()],
        description="The gs1 for each product or part in your warehouse must be unique.",
    )
    description = TextAreaField("description", validators=[validators.Optional()])
    assemblycosts = DecimalField(
        "assemblycosts",
        validators=[validators.DataRequired()],
        description="What does it cost to use this part in a bifer product? A sticker needs to be applied, a jar needs to be filled.",
    )


class ProductAssembleFromPartForm(Form):
    part = SelectField("part")
    amount = IntegerField(
        "amount",
        [validators.NumberRange(min=1, max=65535)],
        description="How many of the selected product are used as parts in the current product?",
    )
    assemblycosts = DecimalField(
        "assemblycosts",
        validators=[validators.DataRequired()],
        description="What does it cost to use the selected product as a part in the current product? A sticker needs to be applied, a jar needs to be filled.",
    )


class ProductAssembleForm(Form):
    amount = IntegerField("amount", [validators.NumberRange(min=1, max=65535)])
    reference = StringField(
        "reference", [validators.Optional(), validators.Length(max=255)]
    )
    lot = StringField("lot", [validators.Optional(), validators.Length(max=45)])
