import decimal
from io import StringIO
import os
from abc import ABC, abstractmethod
from numbers import Number

from uweb3.libs.sqltalk import mysql
from uweb3.templateparser import Parser

from warehouse.common.helpers import BaseFactory
from warehouse.products.helpers.importers.importer import ABCImporter, ProductPair
from warehouse.products.helpers.importers.parser import ABCParser, CSVParser
from warehouse.suppliers import model as supplier_model


class ABCCustomImporter(ABCImporter):
    """Abstract base class that a custom importer should implement."""

    @abstractmethod
    def Import(
        self,
        products: list[supplier_model.Supplierproduct],
    ) -> tuple[list[ProductPair], list[dict]]:
        pass

    @abstractmethod
    def render_results(self):
        """Render data to the user to see what has been processed and/or what
        has failed."""
        pass


class ABCServiceBuilder(ABC):
    """Abstract base class for a service builder."""

    @abstractmethod
    def __call__(self, *args, **kwargs):
        pass


class ABCDatabaseImporter(ABC):
    """Abstract base class for a database importer.
    These importers can be used for bulk actions such as importing
    thousands of new products, or updating them."""

    @abstractmethod
    def add(self, record: dict):
        """Adds a record to the list of data that should be handled in bulk."""
        pass

    @abstractmethod
    def import_all(self):
        """Process all records and execute one bulk action to the database."""
        pass


class CustomRenderedMixin:
    """Mixin class that allows a custom importer/parser to be rendered in a
    template file."""

    def __init__(self):
        self.filename = ""
        self._processed_products = []
        self._unprocessed_products = []
        self._new_imports = []

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
            __new_imports=self._new_imports,
        )


class SolarClarityMissingImporter:
    def __init__(
        self,
        connection,
        supplierID,
    ):
        self.connection = connection
        self.supplierID = supplierID

    def Import(self, record: dict):
        return supplier_model.Supplierproduct.Create(
            self.connection,
            {
                "supplier": self.supplierID,
                "name": record["article_name"],
                "vat": "21",
                "supplier_sku": record["article_number"],
            },
        )


class SolarClarity(CustomRenderedMixin, ABCCustomImporter):
    def __init__(
        self,
        parser: ABCParser,
        missing_supplier_product_handler=None,
    ):
        """Importer/parser combination class for custom imports for SolarClarity.

        Args:
            parser (ABCParser): The parser that retrieves all data from
                the posted supplier csv file.
            missing_supplier_product_handler: The importer that should
                be called whenever a missing product is encountered.
                If no importer is supplied this product will be added
                to the unprocessed list.
        """
        super().__init__()
        # The filename of the template for this custom importer.
        self.filename = "solarclarity.html"
        self.missing_supplier_product_handler = missing_supplier_product_handler
        self.parser = parser
        self.products = []

    def Import(
        self,
        supplier_products: list[supplier_model.Supplierproduct],
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
            data (list[dict]): List of dictionaries containing all the
            suppliers products
        """
        single_products = [
            record for record in data if record["items_per_packing_unit"] == 1
        ]

        for record in single_products:
            product = self._find_product(record)
            match product:
                case supplier_model.Supplierproduct():
                    result = self._import_as_supplier_stock(product, record)
                    self._processed_products.append(
                        ProductPair(parsed_product=record, supplier_product=result)
                    )
                case None if self.missing_supplier_product_handler:
                    self._new_imports.append(
                        self.missing_supplier_product_handler.Import(record)
                    )
                case _:
                    self._unprocessed_products.append(record)

    def _find_product(self, record) -> None | supplier_model.Supplierproduct:
        products = [p for p in self.products if p["name"] == record["article_name"]]
        if products:
            return products[0]
        return None

    def _import_as_supplier_stock(
        self,
        supplier_product: supplier_model.Supplierproduct,
        record: dict,
    ):
        try:
            supplier_product["cost"] = to_decimal(record["gross"])
        except Exception:
            if price := record.get("cost"):
                supplier_product["cost"] = price

        supplier_product["supplier_sku"] = record["article_number"]
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


class SolarClarityServiceBuilder(ABCServiceBuilder):
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
        import_missing=False,
    ):
        self.columns = columns
        self.import_missing = import_missing

    def __call__(
        self,
        file,
        connection,
        supplierID,
        *_,
        importer=SolarClarityMissingImporter,
        **__,
    ):
        parser = CSVParser(file_path=file, columns=self.columns)

        if self.import_missing:
            importer = importer(connection, supplierID)
            return SolarClarity(
                parser=parser,
                missing_supplier_product_handler=importer,
            )
        return SolarClarity(
            parser=parser,
        )


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
        self.register("Solarclarity", SolarClarityServiceBuilder())
        self.register(
            "Solarclarity (import missing products)",
            SolarClarityServiceBuilder(import_missing=True),
        )

    def list_all(self):
        return self._registered_items.keys()
