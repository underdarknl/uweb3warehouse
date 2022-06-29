from abc import ABC, abstractmethod

import pandas
from pandas import errors as pandas_errors
from warehouse.products.helpers.importers.exceptions import ImporterException


class ABCParser(ABC):
    @abstractmethod
    def Parse(self):
        pass


class StockParser(ABCParser):
    def __init__(self, file_path, columns, normalize_columns):
        """Attempts to find the columns and values from a passed html file object.

        Args:
            file_path (StringIO): The StringIO object containing the HTML with
                the table.
            columns (tuple[str]): The columns that we are interested in
            normalize_columns (tuple[str]): The column containing the product
                name that should be normalized to match the database value.
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
            dataframes (list[DataFrame]): List with dataframes found by
                pandas read_html

        Returns:
            list[dict]: Returns the list with the matches.
        """
        # Because multiple tables can be present in a page we can have
        # multiple dataframes.
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
        """Normalize only the columns which are of interest.
        This should be the column containing the product name."""
        clean_result = self._remove_unwanted_keys(result)

        for column in self.normalize_columns:
            clean_result[column] = clean_result[column].replace("/", "_")
        return clean_result

    def _remove_unwanted_keys(self, result):
        """Create a copy of the result and mutate the object by removing
        keys that are not sought after."""
        copy = dict(result)
        for key in result.keys():
            if key not in self.columns:
                del copy[key]
        return copy


class CSVParser(ABCParser):
    def __init__(self, file_path, columns: tuple):
        self.file_path = file_path
        self.columns = columns

    def Parse(self):
        try:
            data = pandas.read_csv(
                self.file_path, skip_blank_lines=True, usecols=self.columns
            )
            data.dropna(how="all", inplace=True)
        except (pandas_errors.ParserError, Exception) as exc:
            raise ImporterException(exc.args) from exc
        return data.to_dict("records")
