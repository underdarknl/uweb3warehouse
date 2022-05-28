import difflib
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
            match[column] = self._normalize_column_value(match[column])

    def _normalize_column_value(self, value):
        match = " ".join(value.split())
        values = [match, match.replace("/", "_")]
        # if "-" in match:
        #     match = match.replace(" ", "_")
        #     match = match.replace("-", "_")
        #     values.append(match)
        # if " " in match:
        #     values.append(match.replace(" ", "_"))
        # if "(" in match:
        #     values.append(match.split("(")[0])
        return values


class StockImporter:
    def __init__(self, connection, results):
        self.results = results
        self.connection = connection
        self.products = None

    def Import(self):
        self.load_product_data()
        for product_list in self.results:
            self._import_list(product_list)

    def load_product_data(self):
        self.products = list(model.Product.List(self.connection))
        self.product_names = [p["name"] for p in self.products]

    def _import_list(self, products):
        for product in products:
            self._import(product)

    def _import(self, result):
        for name in result["Type"]:
            closest_match = difflib.get_close_matches(name, self.product_names, n=1)[0]
            product = next(
                (x for x in self.products if x["name"] == closest_match), None
            )
            return self._add_stock(product, result["Op voorraad"])

    def _add_stock(self, product, amount):
        return model.Stock.Create(
            self.connection,
            {
                "product": product.key,
                "amount": amount,
            },
        )
