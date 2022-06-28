from typing import NamedTuple
from abc import ABC, abstractmethod
from warehouse.products import model
from warehouse.suppliers import model as supplier_model


class ABCImporter(ABC):
    """Abstract base class to indicate which methods should be implemented
    to be considered an importer class."""

    @abstractmethod
    def Import(self):
        pass


class IncompleteImporterMapping(KeyError):
    """Error that is raised when the mapping for an importer is incomplete"""


class ProductPair(NamedTuple):
    """Maps a Supplierproduct to a parsed product for displaying purposes.
    This allows the user to see which imported product mapped to which
    database entry."""

    parsed_product: dict
    supplier_product: supplier_model.Supplierproduct


class StockImporter(ABCImporter):
    def __init__(self, mapping: dict[str, str]):
        """Initialize the importer that will import the stock from the passed results.

        Args:
            mapping (dict): Contains the key value mappings for the columns in the table.
                For example {"amount": "Op voorraad"} would mean that the amount column in the table is named "Op voorraad".
        """
        self._required_keys = ("name", "amount")
        self.supplier_products = []
        self.parsed_results = []

        self.mapping = mapping
        self._processed_products = []
        self._unprocessed_products = []

    def Import(
        self,
        parsed_results: list[list[dict]],
        supplier_products: list[supplier_model.Supplierproduct],
    ) -> tuple[list[ProductPair], list[dict]]:
        """Attempt to find a database product for each result.
        If a product is found, add the stock to the product.

        Args:
            parsed_results (list[list[dict]]): List of dictionaries that were normalized by the StockParser class
            products (list[model.Supplierproduct]): A list of all the products from the supplier that we want to import
        """
        self._validate_mapping()
        self.parsed_results = list(parsed_results)
        self.supplier_products = list(supplier_products)

        for found_product_list in self.parsed_results:
            self._import_parsed_results(found_product_list)

        return self._processed_products, self._unprocessed_products

    def _validate_mapping(self):
        for key in self._required_keys:
            if key not in self.mapping:
                raise IncompleteImporterMapping(
                    f"{key} is a required mapping for the importing process."
                )

    def _import_parsed_results(self, results: list[dict]):
        for product in results:
            self._import_as_supplier_stock(product)

    def _import_as_supplier_stock(self, parsed_product: dict):
        # Find corresponding product by mapping the column name to the database field name.
        # This is because every supplier can have a different naming convention.
        name = parsed_product[self.mapping["name"]]
        product = self._find_product(name)

        if not product:
            return self._add_to_unprocessed(parsed_product)

        self._update_stock(product, parsed_product[self.mapping["amount"]])
        self._add_to_processed(parsed_product, product)

    def _find_product(self, name: str):
        """Attempt to find the closest matching database product for the passed name.

        Args:
            name (str): The name of the product that we want to find.

        Returns:
            product (model.Product): The product that was found to be the best match.
        """
        product = [p for p in self.supplier_products if p["name"] == name]

        if not product:
            return None

        return product[0]

    def _add_to_processed(self, parsed_product, product):
        """Adds the parsed_product from the parsed file and the database product to a tuple
        and adds it to the processed_products list. The keys from the parsed_products are
        normalized before adding them to the list, this allows us to display parsed_products
        from different suppliers with the same key names.

        Args:
            parsed_product (_type_): The product that was found by the parser.
            product (model.Product): The product that was found in the database.
        """
        normalized_result = self._normalize_keys(parsed_product)
        self._processed_products.append(ProductPair(normalized_result, product))

    def _add_to_unprocessed(self, parsed_product):
        normalized_result = self._normalize_keys(parsed_product)
        self._unprocessed_products.append(normalized_result)

    def _normalize_keys(self, result):
        """Normalize the keys of the result dictionary so that they match the database field names."""
        return {key: result[self.mapping[key]] for key in self.mapping.keys()}

    def _update_stock(self, product, amount):
        """Update the stock of the product with the amount that was found in the parsed file.

        Args:
            product (model.Product): The product that was found in the database.
            amount (int): The amount that was found in the parsed file (this is the current stock of the supplier)

        Returns:
            model.Stock: The added Stock record.
        """
        product["supplier_stock"] = amount
        product.Save()
        return product.Refresh()


class CsvImporter(StockImporter):
    def Import(
        self, parsed_results: list[dict], supplier_products: list[supplier_model.Supplierproduct]
    ) -> tuple[list[ProductPair], list[dict]]:
        """Attempt to find a database product for each result.
        If a product is found, add the stock to the product.

        Args:
            parsed_results (list[dict]): List of dictionaries that were normalized by the StockParser class
            supplier_products (list[model.Supplierproduct]): A list of all the products from the supplier that we want to import
        """
        self._validate_mapping()
        self.parsed_results = list(parsed_results)
        self.supplier_products = list(supplier_products)
        self._import_parsed_results(self.parsed_results)
        return self._processed_products, self._unprocessed_products
