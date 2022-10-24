import decimal
import types
from typing import Iterable, Iterator, NamedTuple

from warehouse.common import helpers as common_helpers
from warehouse.products import model


class ProductDTO(NamedTuple):
    name: str
    product: str
    sku: str


class ProductPriceDTO(NamedTuple):
    ID: int
    price: decimal.Decimal
    start_range: int


class ProductDTOService:
    def to_dto(
        self,
        product: model.Product | list[model.Product] | Iterable[model.Product],
    ) -> ProductDTO | list[ProductDTO]:
        """Converts either a single Product object, or any iterable to the DTO
        representation object.

        Args:
            product (model.Product | list[model.Product] |
            Iterable[model.Product]): The single Product a iterable of
            Products to convert to DTO

        Raises:
            TypeError: Raised when the product object is of an
            unsupported type.

        Returns:
            ProductDTO|list[ProductDTO]: Single object or list
            containing the DTO's of all passed objects.
        """
        match product:  # noqa: E999
            case [model.Product(), *_]:
                return self._convert_list(product)
            case types.GeneratorType():
                to_list = list(product)
                return self.to_dto(to_list)
            case model.Product():
                return self._convert(product)
            case []:
                return []
            case _:
                raise TypeError("Product did not match any known type.")

    def _convert_list(self, products):
        items = []
        for product in products:
            items.append(self._convert(product))
        return items

    def _convert(self, product):
        return ProductDTO(
            name=product["name"],
            product=product["ID"],
            sku=product["sku"],
        )._asdict()


class ProductPriceDTOService:
    """Converts the Productprice model class to a DTO object for API usage."""

    def to_dto(
        self,
        product_price: model.Productprice
        | list[model.Productprice]
        | Iterator[model.Productprice],
    ) -> ProductPriceDTO | list[ProductPriceDTO]:
        """Converts either a single Productprice object, or any iterable to the DTO
        representation object.

        Args:
            product_price (model.Productprice | list[model.Productprice] |
            Iterator[model.Productprice]): The target object to convert to DTO.

        Raises:
            ValueError: Raised when the product_price object is of an
            unsupported type.

        Returns:
            ProductPriceDTO | list[ProductPriceDTO]: Single object or list
            containing the DTO's of all passed objects.
        """
        match product_price:
            case [model.Productprice(), *_]:
                return self._convert_list(product_price)
            case types.GeneratorType():
                to_list = list(product_price)
                return self.to_dto(to_list)
            case model.Productprice():
                return self._convert(product_price)  # type: ignore
            case []:
                return []
            case _:
                raise TypeError("Product price dit not match any known price")

    def _convert_list(self, product_prices: list[model.Productprice]):
        items = []
        for product in product_prices:
            items.append(self._convert(product))
        return items

    def _convert(self, product_price_obj: model.Productprice) -> ProductPriceDTO:
        return ProductPriceDTO(
            ID=product_price_obj["ID"],  # type: ignore
            price=product_price_obj["price"],  # type: ignore
            start_range=product_price_obj["start_range"],  # type: ignore
        )._asdict()


class DtoManager(common_helpers.BaseFactory):
    def __init__(self):
        super().__init__()
        self.register_base_handlers()

    def register_base_handlers(self):
        self.register("product", ProductDTOService)
        self.register("product_price", ProductPriceDTOService)


def remove_stock(connection, sku, amount, reference=None):
    product = model.Product.FromSku(connection, sku)
    currentstock = product.currentstock
    if (
        amount < 0 and abs(amount) > currentstock  # only assemble when we sell
    ):  # only assemble when we have not enough stock
        try:
            product.Assemble(
                abs(amount)
                - currentstock,  # only assemble what is missing for this sale
                "Assembly for %s" % reference,
            )
        except model.AssemblyError as error:
            raise ValueError(error.args[0])

    # only assemble when we sell
    if amount < 0 and abs(amount) > currentstock:
        # only assemble when we have not enough stock
        product.Assemble(
            abs(amount) - currentstock,  # only assemble what is missing for this sale
            "Assembly for %s" % reference,
        )
    model.Stock.Create(
        connection,
        {
            "product": product,
            "amount": amount,
            "reference": reference,
        },
    )
    return {
        "stock": product.currentstock,
        "possible_stock": product.possiblestock,
    }


def add_stock(connection, sku, amount, reference=None):
    """Used to refund after an invoice is canceled.
    This is an addition to stock.

    Args:
        connection (PageMaker.connection): The connection object
        sku (str): The product SKU
        amount (int): The amount to refund
        reference (str, optional): The description for the refund
    """
    product = model.Product.FromSku(connection, sku)
    model.Stock.Create(
        connection,
        {
            "product": product,
            "amount": amount,
            "reference": reference,
        },
    )


def possibleparts_select_list(possibleparts):
    return [(p["sku"], f"{p['sku']} - {p['name']}") for p in possibleparts]


def suppliers_select_list(suppliers):
    return [(s["ID"], s["name"]) for s in suppliers]
