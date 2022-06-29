from io import StringIO

from warehouse.products import helpers as product_helpers
from warehouse.products import model as product_model
from warehouse.suppliers import forms, model


def import_stock_from_file(supplier_stock_form, supplier, connection):
    """Attempts to import the stock from the file that was uploaded.

    Args:
        supplier_stock_form (forms.ImportSupplierStock): The form used
            to upload the file and specify the column names
        supplier (model.Supplier): The supplier object
            connection (PageMaker.connection): Connection object to access
            the database

    Returns:
        (list(Product), list(ProductPair)): List containing the processed
            Products and a list containing the ProductPairs of
            unprocessed products.

    Raises:
        KeyError: If the column names are not found in the file.
    """
    parsed_data = _parse_file(supplier_stock_form)
    products = model.Supplierproduct.Products(connection, supplier)
    importer = _setup_importer(supplier_stock_form)
    return importer.Import(
        parsed_data,
        products,
    )


def _parse_file(supplier_stock_form):
    file = supplier_stock_form.fileupload.data[0]
    parser = product_helpers.StockParser(
        file_path=StringIO(file["content"]),
        columns=(
            supplier_stock_form.column_name_mapping.data,
            supplier_stock_form.column_stock_mapping.data,
        ),
        normalize_columns=(supplier_stock_form.column_name_mapping.data,),
    )

    return parser.Parse()


def _setup_importer(supplier_stock_form):
    return product_helpers.StockImporter(
        {
            "name": supplier_stock_form.column_name_mapping.data,
            "amount": supplier_stock_form.column_stock_mapping.data,
        },
    )


def get_supplier_product_form(connection, supplier, postdata):
    products = product_model.Product.List(connection)
    form = forms.SupplierAddProductForm(postdata, prefix="sup")
    form.supplier.choices = [(supplier["ID"], supplier["name"])]
    form.product.choices = [(p["ID"], p["name"]) for p in products]
    return form


def get_importer_prefix(supplier):
    """Generate a prefix based on the supplier.

    This allows the browser to remember the column names for the specific supplier.

    Args:
        supplier (model.Supplier): The supplier object.

    Returns:
        str: The prefix for the wtform.
    """
    return f"import-supplier-stock-{supplier['ID']}"
