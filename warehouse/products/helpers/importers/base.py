from abc import ABC, abstractmethod
from typing import NamedTuple

from warehouse.suppliers import model as supplier_model


class ProductPair(NamedTuple):
    """Maps a Supplierproduct to a parsed product for displaying purposes.
    This allows the user to see which imported product mapped to which
    database entry."""

    parsed_product: dict
    supplier_product: supplier_model.Supplierproduct


class ABCParser(ABC):
    @abstractmethod
    def Parse(self):
        pass


class ABCImporter(ABC):
    """Abstract base class to indicate which methods should be implemented
    to be considered an importer class."""

    @abstractmethod
    def Import(self):
        pass


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
    """Abstract base class for database updater."""

    @abstractmethod
    def update(
        self,
        record: dict,
        supplier_product: supplier_model.Supplierproduct,
    ) -> supplier_model.Supplierproduct:
        pass
