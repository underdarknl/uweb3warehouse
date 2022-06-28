from typing import NamedTuple

import pandas

from warehouse.products import model
from warehouse.suppliers import model as supplier_model
from warehouse.common.helpers import BaseFactory


class IncompleteImporterMapping(KeyError):
    """Error that is raised when the mapping for an importer is incomplete"""


class ProductPair(NamedTuple):
    parsed_product: dict
    supplier_product: supplier_model.Supplierproduct


class StockParser:
    def __init__(self, file_path, columns, normalize_columns):
        """Attempts to find the columns and values from a passed html file object.

        Args:
            file_path (StringIO): The StringIO object containing the HTML with the table.
            columns (tuple[str]): The columns that we are interested in
            normalize_columns (tuple[str]): The column containing the product name that should be normalized to match the database value.
        """
        self.columns = columns
        self.normalize_columns = normalize_columns
        self.file_path = file_path

    def Parse(self):
        """Start the parsing process."""
        dataframes = self._parse()
        return self._process_dataframes(dataframes)

    def _parse(self):
        """Read the file and attempt to find the columns."""
        return pandas.read_html(self.file_path, header=0)

    def _process_dataframes(self, dataframes):
        """Process the list of dataframes containing table elements.

        Args:
            dataframes (list[DataFrame]): List with dataframes found by pandas.read_html

        Returns:
            list[dict]: Returns the list with the matches.
        """
        # Because multiple tables can be present in a page we can have multiple dataframes.
        return [
            self._process_dataframe(dataframe.to_dict("record"))
            for dataframe in dataframes
        ]

    def _process_dataframe(self, dataframe):
        """Process the dataframe by normalizing the values contained in the columns.

        Returns:
            list[dict]: A list of dictionaries with the processed matches.
        """
        results = []

        for result in dataframe:
            if any(
                missing_columns := [
                    column for column in self.columns if column not in result.keys()
                ]
            ):
                raise KeyError(
                    f"The following columns could not be found: {missing_columns}"
                )

            results.append(self._normalize(result))

        return results

    def _normalize(self, result):
        """Normalize only the columns which are of interest. This should be the column containing the product name."""
        clean_result = self._remove_unwanted_keys(result)

        for column in self.normalize_columns:
            clean_result[column] = clean_result[column].replace("/", "_")
        return clean_result

    def _remove_unwanted_keys(self, result):
        """Create a copy of the result and mutate the object by removing keys that are not sought after."""
        copy = dict(result)
        for key in result.keys():
            if key not in self.columns:
                del copy[key]
        return copy


class StockImporter:
    def __init__(self, mapping: dict[str, str]):
        """Initialize the importer that will import the stock from the passed results.

        Args:
            mapping (dict): Contains the key value mappings for the columns in the table.
                For example {"amount": "Op voorraad"} would mean that the amount column in the table is named "Op voorraad".
        """
        self._required_keys = ("name", "amount")
        self.products = []
        self.parsed_results = []

        self.mapping = mapping
        self._processed_products = []
        self._unprocessed_products = []

    def Import(
        self, parsed_results: list[list[dict]], products: list[model.Product]
    ) -> tuple[list[ProductPair], list[dict]]:
        """Attempt to find a database product for each result.
        If a product is found, add the stock to the product.

        Args:
            parsed_results (list[list[dict]]): List of dictionaries that were normalized by the StockParser class
            products (list[model.Product]): A list of all the products from the supplier that we want to import
        """
        self._validate_mapping()
        self.parsed_results = list(parsed_results)
        self.products = list(products)

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
        product = [p for p in self.products if p["name"] == name]

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


def csv_parser(file, interested_columns: tuple):
    data = pandas.read_csv(file, skip_blank_lines=True, usecols=interested_columns)
    data.dropna(how="all", inplace=True)
    return data.to_dict("records")


class CsvImporter(StockImporter):
    def Import(
        self, parsed_results: list[dict], products: list[model.Product]
    ) -> tuple[list[ProductPair], list[dict]]:
        """Attempt to find a database product for each result.
        If a product is found, add the stock to the product.

        Args:
            parsed_results (list[dict]): List of dictionaries that were normalized by the StockParser class
            products (list[model.Product]): A list of all the products from the supplier that we want to import
        """
        self._validate_mapping()
        self.parsed_results = list(parsed_results)
        self.products = list(products)
        self._import_parsed_results(self.parsed_results)
        return self._processed_products, self._unprocessed_products


class ParserFactory(BaseFactory):
    """Factory class to keep track of all supported parsers"""

    def register_base_classes(self):
        self.register("html_table", StockParser)
        self.register("csv", csv_parser)


if __name__ == "__main__":
    x = csv_parser("/home/stef/Downloads/pricelist_short.csv", ("article_number",))
    print(x)
