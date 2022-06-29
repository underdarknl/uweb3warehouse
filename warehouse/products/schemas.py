from marshmallow import EXCLUDE, Schema, fields, post_load
from marshmallow.validate import Range


class ProductSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    sku = fields.Str(required=True, allow_none=False)
    quantity = fields.Integer(
        required=True,
        allow_none=False,
        validate=[Range(min=1, error="Product quantity must be at least 1.")],
    )


class BulkRefundSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    products = fields.Nested(ProductSchema, many=True, required=True)
    reference = fields.Str(max=45, load_default="")


class BulkStockSchema(BulkRefundSchema):
    @post_load
    def negative_quantity(self, in_data, **kwargs):
        for product in in_data["products"]:
            product["quantity"] = -abs(product["quantity"])
        return in_data
