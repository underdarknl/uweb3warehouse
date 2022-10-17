from wtforms import (
    IntegerField,
    SelectField,
    StringField,
    validators,
    FieldList,
    FormField,
    HiddenField,
    ValidationError,
)

from warehouse.common.helpers import BaseForm


class EitherOtherRequired(validators.DataRequired):
    """Validator that ensures that at least one of the dependant_fields
    contains a value."""

    def __init__(self, dependant_fields, *args, **kwargs):
        """_summary_

        Args:
            dependant_fields (iterable): An iterable containing the names of the
            dependant fields. For example: either one or both fields needs to
            be filled in, field_one or field_two. The code required:
                    StringField(
                        "field_one",
                        validators=[
                                    EitherOtherRequired(
                                        dependant_fields=("field_two",)
                                    )
                                ]
                    )
                    StringField(
                        "field_two",
                        validators=[validators.Optional()]
                    )
        """
        super().__init__(*args, **kwargs)
        self.field_flags = {}
        self.dependant_fields = dependant_fields

    def __call__(self, form, field):
        possibly_required = [form._fields.get(field) for field in self.dependant_fields]

        if field.errors:
            raise validators.StopValidation()

        if bool(field.data):
            return super().__call__(form, field)

        if not any(bool(field.data) for field in possibly_required):
            raise ValidationError(
                "At least one of the following fields is required: "
                f"""'{field.name}, {"".join(str(x) for x in self.dependant_fields)}'"""
            )

        field.errors[:] = []
        raise validators.StopValidation()


class OrderProduct(BaseForm):
    ID = HiddenField("ID")
    product_sku = StringField(
        "product_sku",
        validators=[validators.InputRequired()],
        render_kw={"readonly": True},
    )
    quantity = IntegerField(
        "quantity",
        validators=[validators.NumberRange(min=1, max=65535)],
        render_kw={"readonly": True},
    )
    description = StringField(
        "description", validators=[validators.Optional(), validators.Length(max=255)]
    )


class CreateOrderForm(BaseForm):
    ID = HiddenField("ID")
    description = StringField(
        "description",
        validators=[validators.InputRequired()],
        render_kw={"readonly": True},
    )
    reference = StringField(
        "reference",
        validators=[validators.Optional(), validators.Length(max=30)],
        render_kw={"readonly": True},
    )
    status = SelectField(
        "status",
        choices=[
            ("new", "new"),
            ("reservation", "reservation"),
            ("completed", "completed"),
            ("canceled", "canceled"),
        ],
    )
    products = FieldList(FormField(OrderProduct), min_entries=1)


class OrderFromIdOrReferenceForm(BaseForm):
    ID = IntegerField(
        "orderID", validators=[EitherOtherRequired(dependant_fields=("reference",))]
    )

    reference = StringField(
        "reference", validators=[validators.Optional(), validators.Length(max=30)]
    )
