from warehouse.common.helpers import BaseFactory
from warehouse.products.helpers.importers.parser import StockParser, csv_parser


class SolarCity:
    def __init__(self, data):
        self.data = data


class ParserFactory(BaseFactory):
    """Factory class to keep track of all supported parsers"""

    def register_base_classes(self):
        # self.register("html_table", StockParser)
        # self.register("csv", csv_parser)
        self.register("solar_city", SolarCity)


if __name__ == "__main__":
    x = SolarCity([{}])
