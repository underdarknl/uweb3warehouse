import decimal
import os
from abc import ABC, abstractmethod
from numbers import Number
from typing import Any

from uweb3.templateparser import Parser

from warehouse.common.helpers import BaseFactory
from warehouse.products.helpers.importers.importer import ABCImporter, ProductPair
from warehouse.products.helpers.importers.parser import ABCParser, CSVParser
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


class ABCServiceBuilder(ABC):
    @abstractmethod
    def __call__(self):
        pass


class CustomRenderedMixin:
    """Mixin class that allows a custom importer/parser to be rendered in a
    template file."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = ""

    @property
    def render_results(self):
        """Render the template for the custom importer class."""
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
        """Importer/parser combination class for custom imports for Solarcity.

        Args:
            parser (ABCParser): The parser that retrieves all data from
                the posted supplier csv file.
        """
        # The filename of the template for this custom importer.
        self.filename = "solarcity.html"
        self.parser = parser
        self.products = []
        self._processed_products = []
        self._unprocessed_products = []

    def Import(
        self, supplier_products: list[supplier_model.Supplierproduct]
    ) -> tuple[list[ProductPair], list[dict]]:
        """Parse csv file and import found results into the corresponding
        Supplierproduct record in the database.

        Args:
            supplier_products (list[supplier_model.Supplierproduct]): A list
                of Supplierproducts for the given supplier that we are importing
                products for.

        Returns:
            tuple[list[ProductPair], list[dict]]: processed, unprocessed
                the processed list contains pairs that map a Supplierproduct
                to the found record from the csv.
                The unprocessed list contains raw dictionaries for which
                no results could be found.

        """
        self.products = list(supplier_products)
        data = self.parser.Parse()
        self._process(data)
        return self._processed_products, self._unprocessed_products

    def _process(self, data):
        """Process csv data and update the Supplierproduct record.

        Currently there is no support for bulk price reductions so we only save
        the piece price for each Supplierproduct.

        Args:
            data (list[dict]): List of dictionaries containing all the suppliers products
        """
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


class SolarCityServiceBuilder(ABCServiceBuilder):
    def __init__(
        self,
        columns=(
            "article_number",
            "article_name",
            "product_reference",
            "packing_unit",
            "items_per_packing_unit",
            "gross",
        ),
    ):
        self.columns = columns

    def __call__(self, file, *_, **__):
        parser = CSVParser(file_path=file, columns=self.columns)
        return SolarCity(parser=parser)


class CustomImporters(BaseFactory):
    """Factory class to keep track of all supported parsers"""

    def __init__(self):
        super().__init__()
        self.register_base_classes()

    def get_registered_item(self, key, *args, **kwargs) -> ABCCustomImporter:
        """Retrieves a registered importer from the factory.

        Args:
            key (str): The name of the importer

        Returns:
            ABCCustomImporter: The importer class implementing
                the ABCCustomImporter base class.
        """

        return super().get_registered_item(key, *args, **kwargs)

    def register_base_classes(self):
        self.register("Solarcity", SolarCityServiceBuilder())

    def list_all(self):
        return self._registered_items.keys()
