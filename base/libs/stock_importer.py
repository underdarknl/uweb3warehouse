import difflib
from collections import namedtuple
from dataclasses import dataclass
from fileinput import close

import pandas

from base import model


class StockParser:
    def __init__(self, file_path, columns, normalize_columns):
        self.columns = columns
        self.normalize_columns = normalize_columns
        self.file_path = file_path

    def Parse(self):
        results = self._parse()
        return self._matches(results)

    def _parse(self):
        return pandas.read_html(self.file_path, header=0, parse_dates=True)

    def _matches(self, results):
        processed = []
        for matches in results:
            processed.append(self._process_matches(matches.to_dict("record")))
        return processed

    def _process_matches(self, matches):
        for match in matches:
            self._normalize(match)
        return matches

    def _normalize(self, match):
        for column in self.normalize_columns:
            match[column] = match[column].replace("/", "_")


class StockImporter:
    def __init__(self, connection, results, mapping):
        self.processed_products = []
        self.unprocessed_products = []
        self.connection = connection
        self.mapping = mapping
        self.results = results
        self.products = list(model.Product.List(self.connection))
        self.product_names = [p["name"] for p in self.products]

    def Import(self):
        for product_list in self.results:
            self._import_products(product_list)

    def _import_products(self, products):
        for product in products:
            self._import_product(product)

    def _import_product(self, result):
        name = result[self.mapping["name"]]
        product = self._find_product(name)

        if not product:
            self.unprocessed_products.append(self._normalize_keys(result))
            return

        self._add_stock(product, result[self.mapping["amount"]])
        self._add_to_processed(result, product)

    def _find_product(self, name):
        closest_matches = difflib.get_close_matches(
            name, self.product_names, n=3, cutoff=0.8
        )
        if not closest_matches:
            return None
        return next((x for x in self.products if x["name"] == closest_matches[0]), None)

    def _add_to_processed(self, result, product):
        pair = namedtuple("ProductPair", "parsed_product product".split())
        normalized_result = self._normalize_keys(result)
        self.processed_products.append(pair(normalized_result, product))

    def _normalize_keys(self, result):
        return {key: result[self.mapping[key]] for key in self.mapping.keys()}

    def _add_stock(self, product, amount):
        print(product, amount)
        # return model.Stock.Create(
        #     self.connection,
        #     {
        #         "product": product.key,
        #         "amount": amount,
        #     },
        # )
