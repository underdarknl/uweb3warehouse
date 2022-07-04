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


def refined_search(record: dict, products: list):
    sought_article_number = record["article_number"]
    sought_name = record["article_name"]

    for match in products:
        match match:
            case {"supplier_sku": article_number, "name": name} if str(
                article_number
            ) == str(sought_article_number) and name == sought_name:
                return match
            case {"name": name} if name == sought_name:
                return match
            case _:
                pass
    return None


def find_match(record: dict, products: list):
    if "article_number" in record:
        return refined_search(record, products)

    try:
        return next(p for p in products if p["name"] == record["article_name"])
    except StopIteration:
        return None


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
    def add(self, record: dict) -> dict:
        """Adds a record to the list of data that should be handled in bulk."""
        pass

    @abstractmethod
    def import_all(self):
        """Process all records and execute one bulk action to the database."""
        pass


class ABCDatabaseUpdater(ABC):
    @abstractmethod
    def update(
        self,
        record: dict,
        supplier_product: supplier_model.Supplierproduct,
    ) -> supplier_model.Supplierproduct:
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


class SolarClarityMissingImporter(ABCDatabaseImporter):
    """Handles bulk insertion of Supplierrecords for SolarClarity import."""

    def __init__(
        self,
        connection: mysql.connection.Connection,
        supplierID: int,
    ):
        self.connection = connection
        self.supplierID = supplierID
        self.insert_list = []

    def add(self, record: dict, default_vat=21) -> dict:
        """Add a record to the list of values that should be inserted."""
        price = to_decimal(record["gross"])
        self.insert_list.append(
            (
                self.supplierID,
                record["article_name"],
                price,
                default_vat,
                record["article_number"],
            )
        )
        return {
            "supplier": self.supplierID,
            "name": record["article_name"],
            "price": price,
            "vat": default_vat,
            "supplier_sku": record["article_number"],
        }

    def import_all(self):
        """Import all records in the insert_list in bulk to prevent long
        loading times on mysql insert."""
        with self.connection as cursor:
            cursor.executemany(
                """INSERT INTO supplierproduct(supplier, name, cost, vat, supplier_sku)
                VALUES (%s, %s, %s, %s, %s);""",
                self.insert_list,
            )


class SolarClarityRecordUpdate(ABCDatabaseUpdater):
    """Handle bulk record update for SolarClarity importer."""

    def __init__(self, connection: mysql.connection.Connection):
        self.connection = connection
        self.update_list = []

    def update(
        self,
        record: dict,
        supplier_product: supplier_model.Supplierproduct,
    ):
        try:
            supplier_product["cost"] = to_decimal(record["gross"])
        except Exception:
            if price := record.get("cost"):
                supplier_product["cost"] = price

        supplier_product["supplier_sku"] = record["article_number"]
        supplier_product.Save()
        return supplier_product


class SolarClarity(CustomRenderedMixin, ABCCustomImporter):
    def __init__(
        self,
        parser: ABCParser,
        supplier_product_updater: ABCDatabaseUpdater,
        missing_supplier_product_handler: ABCDatabaseImporter | None = None,
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
        self.updater = supplier_product_updater
        self.missing_importer = missing_supplier_product_handler
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
            record for record in data if int(record["items_per_packing_unit"]) == 1
        ]

        for record in single_products:
            self._process_record(record)

        if self._new_imports and self.missing_importer:
            self.missing_importer.import_all()

    def _process_record(self, record):
        supplier_product = find_match(record, self.products)

        match supplier_product:
            case supplier_model.Supplierproduct():
                result = self.updater.update(record, supplier_product)
                pair = ProductPair(parsed_product=record, supplier_product=result)
                self._processed_products.append(pair)
            case None if self.missing_importer:
                self._new_imports.append(self.missing_importer.add(record))
            case _:
                self._unprocessed_products.append(record)


def to_decimal(csv_value: str | int) -> decimal.Decimal:
    """Attempt to parse found value to decimal value.

    Handles values like:
        10.25
        10,25
        €10
        €10.25
        €10,25
        1.059.50
        €1.059.50
        €1,059,50
    """
    match csv_value:
        case Number():
            return decimal.Decimal(csv_value).quantize(
                decimal.Decimal(".01"), rounding=decimal.ROUND_UP
            )
        case str():
            if "€" in csv_value:
                csv_value = csv_value.split("€")[1]

            csv_value = csv_value.replace(",", ".")
            csv_value = csv_value.replace(".", "", (csv_value.count(".") - 1))
            csv_value = csv_value.strip()
            return decimal.Decimal(csv_value).quantize(
                decimal.Decimal(".01"), rounding=decimal.ROUND_UP
            )
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
        file: StringIO,
        connection: mysql.connection.Connection,
        supplierID: int,
        *_,
        importer=SolarClarityMissingImporter,
        record_updater=SolarClarityRecordUpdate,
        **__,
    ):
        """Setup a SolarClarity importer with all required parameters.

        Supports a regular importer and an importer that adds
        missing Supplierproducts to the database as new records with
        the data that is available from Solarclarity."""
        parser = CSVParser(file_path=file, columns=self.columns)

        if self.import_missing:
            importer = importer(connection, supplierID)
            return SolarClarity(
                parser=parser,
                supplier_product_updater=record_updater(connection),
                missing_supplier_product_handler=importer,
            )
        return SolarClarity(
            supplier_product_updater=record_updater(connection),
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
