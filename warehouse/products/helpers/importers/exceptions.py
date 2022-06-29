class ImporterException(Exception):
    """Base exception class for importer related actions."""


class IncompleteImporterMapping(ImporterException):
    """Error that is raised when the mapping for an importer is incomplete."""


class MissingColumnException(ImporterException):
    """Error that is raised when columns are missing on parsing file."""
