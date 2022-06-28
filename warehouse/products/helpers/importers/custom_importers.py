from abc import abstractmethod
from numbers import Number
import os
from uweb3.templateparser import Parser
import decimal
from typing import Any, Callable
from warehouse.common.helpers import BaseFactory
from warehouse.products.helpers.importers.parser import (
    ABCParser,
    CSVParser,
)
from warehouse.products.helpers.importers.importer import ABCImporter, ProductPair
from warehouse.suppliers import model as supplier_model


class ABCCustomImporter(ABCImporter):
    @abstractmethod
    def Import(
        self, products: list[supplier_model.Supplierproduct]
    ) -> tuple[list[ProductPair], list[dict]]:
        pass

    @abstractmethod
    def render_results(self):
        pass


class CustomRenderedMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = ""

    @property
    def render_results(self):
        return Parser(
            path=os.path.join(os.path.dirname(__file__), "custom_template"),
            templates=(
                os.path.join(
                    os.path.dirname(__file__), f"custom_template/{self.filename}"
                ),
            ),
        ).Parse(
            self.filename,
            __processed=self._processed_products,  # type: ignore
            __unprocessed=self._unprocessed_products,  # type: ignore
        )


class SolarCity(CustomRenderedMixin, ABCCustomImporter):
    def __init__(self, parser: ABCParser):
        self.filename = "solarcity.html"
        self.parser = parser
        self.products = []
        self._processed_products = []
        self._unprocessed_products = []

    def Import(
        self, products: list[supplier_model.Supplierproduct]
    ) -> tuple[list[ProductPair], list[dict]]:
        self.products = list(products)
        data = self.parser.Parse()
        self._process(data)
        return self._processed_products, self._unprocessed_products

    def _process(self, data):
        single_products = [
            record for record in data if record["items_per_packing_unit"] == 1
        ]

        for record in single_products:
            product = self._find_product(record)

            if product:
                result = self._import_as_supplier_stock(product, record)
                self._processed_products.append(
                    ProductPair(parsed_product=record, supplier_product=result)
                )
            else:
                self._unprocessed_products.append(record)

    def _find_product(self, record) -> None | supplier_model.Supplierproduct:
        products = [p for p in self.products if p["name"] == record["article_name"]]
        if products:
            return products[0]
        return None

    def _import_as_supplier_stock(
        self, supplier_product: supplier_model.Supplierproduct, record: dict
    ):
        try:
            price = to_decimal(record["gross"])
        except Exception:
            price = record["cost"]

        supplier_product["supplier_sku"] = record["article_number"]
        supplier_product["cost"] = price
        supplier_product.update()
        supplier_product.Save()
        return supplier_product.Refresh()


def to_decimal(csv_value: str | int) -> decimal.Decimal:
    # TODO handle edge cases
    match csv_value:
        case Number():
            return decimal.Decimal(csv_value)
        case str():
            if "€" in csv_value:
                csv_value = csv_value.split("€")[1]

            csv_value = csv_value.replace(",", ".")
            csv_value = csv_value.strip()
            return decimal.Decimal(csv_value)
        case _:
            raise ValueError(f"Unsupported currency value {csv_value}")


class SolarCityServiceBuilder:
    def __call__(self, file, *args, **kwargs) -> ABCCustomImporter:
        parser = CSVParser(
            file_path=file,
            columns=(
                "article_number",
                "article_name",
                "product_reference",
                "packing_unit",
                "items_per_packing_unit",
                "gross",
            ),
        )
        return SolarCity(parser=parser)


class CustomImporters(BaseFactory):
    """Factory class to keep track of all supported parsers"""

    def __init__(self):
        super().__init__()
        self.register_base_classes()

    def get_registered_item(
        self, key, *args, **kwargs
    ) -> Callable[[Any], CustomImporter]:
        return super().get_registered_item(key, *args, **kwargs)

    def register_base_classes(self):
        self.register("Solarcity", SolarCityServiceBuilder)

    def list_all(self):
        return self._registered_items.keys()