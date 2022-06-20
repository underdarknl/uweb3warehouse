import decimal
import difflib
import types
from typing import Iterable, Iterator, NamedTuple

import pandas

from warehouse.common import helpers as common_helpers
from warehouse.products import model
from warehouse.suppliers import model as supplier_model


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
    def __init__(self, connection, mapping, supplier):
        """Initialize the importer that will import the stock from the passed results.

        Args:
            connection (self.connection): Uweb3 connection object
            mapping (dict): Contains the key value mappings for the columns in the table.
                For example {"amount": "Op voorraad"} would mean that the amount column in the table is named "Op voorraad".
            supplier (model.Supplier): The supplier that we want to import the stock for.
        """
        self.products = None
        self.product_names = None
        self.parsed_results = None

        self.mapping = mapping
        self.supplier = supplier
        self._processed_products = []
        self._unprocessed_products = []
        self.connection = connection

    def Import(self, parsed_results, products):
        """Attempt to find a database product for each result.
        If a product is found, add the stock to the product.

        Args:
            parsed_results (list[dict]): List of dictionaries that were normalized by the StockParser class
            products (list[model.Product]): A list of all the products from the supplier that we want to import
        """
        self.parsed_results = list(parsed_results)
        self.products = list(products)
        self.product_names = [p["name"] for p in self.products]

        for found_product_list in self.parsed_results:
            self._import_products(found_product_list)

        return self._processed_products, self._unprocessed_products

    def _import_products(self, products):
        for product in products:
            self._import_product(product)

    def _import_product(self, parsed_product):
        # Find corresponding product by mapping the column name to the database field name.
        # This is because every supplier can have a different naming convention.
        name = parsed_product[self.mapping["name"]]
        product = self._find_product(name)

        if not product:
            self._unprocessed_products.append(self._normalize_keys(parsed_product))
            return

        self._update_stock(product, parsed_product[self.mapping["amount"]])
        self._add_to_processed(parsed_product, product)

    def _find_product(self, name):
        """Attempt to find the closest matching database product for the passed name.

        Args:
            name (str): The name of the product that we want to find.

        Returns:
            product (model.Product): The product that was found to be the best match.
        """
        closest_matches = difflib.get_close_matches(
            name, self.product_names, n=1, cutoff=0.9
        )
        if not closest_matches:
            return None
        return next((x for x in self.products if x["name"] == closest_matches[0]), None)

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


def remove_stock(connection, sku, amount, reference=None):
    product = model.Product.FromSku(connection, sku)
    currentstock = product.currentstock

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


class ProductDTO(NamedTuple):
    name: str
    product: str
    vat: decimal.Decimal
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
            product (model.Product | list[model.Product] | Iterable[model.Product]): The single Product a iterable of Products to convert to DTO

        Raises:
            TypeError: Raised when the product object is of an unsupported type.

        Returns:
            ProductDTO|list[ProductDTO]: Single object or list containing the DTO's of all passed objects.
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
            vat=product["vat"],
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
            product_price (model.Productprice | list[model.Productprice] | Iterator[model.Productprice]): The target object to convert to DTO.

        Raises:
            ValueError: Raised when the product_price object is of an unsupported type.

        Returns:
            ProductPriceDTO | list[ProductPriceDTO]: Single object or list containing the DTO's of all passed objects.
        """
        match product_price:
            case [model.Productprice(), *_]:
                return self._convert_list(product_price)
            case types.GeneratorType():
                to_list = list(product_price)
                return self.to_dto(to_list)
            case model.Productprice():
                return self._convert(product_price)  # type: ignore this is because a model object is a dict.
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
