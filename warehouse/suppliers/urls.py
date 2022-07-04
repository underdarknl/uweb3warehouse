from warehouse.suppliers import api, supplier

api_urls = [
    (
        "/api/v1/supplier/findproduct",
        (api.PageMaker, "find_supplier_product"),
    ),
]

urls = [
    (
        "/suppliers",
        (supplier.PageMaker, "RequestSupplierNew"),
        "POST",
    ),
    (
        "/supplier/updatestock/([^/]*)",
        (supplier.PageMaker, "UpdateSupplierStock"),
        "POST",
    ),
    (
        "/supplier/custom/updatestock/([^/]*)",
        (supplier.PageMaker, "CustomUpdateSupplierStock"),
        "POST",
    ),
    (
        "/suppliers",
        (supplier.PageMaker, "RequestSuppliers"),
    ),
    (
        "/supplier/([^/]*)",
        (supplier.PageMaker, "RequestSupplierSave"),
        "POST",
    ),
    (
        "/supplier/([^/]*)",
        (supplier.PageMaker, "RequestSupplier"),
        "GET",
    ),
    (
        "/supplier/([^/]*)/products",
        (supplier.PageMaker, "RequestSupplierProducts"),
    ),
    (
        "/supplier/([^/]*)/products/([0-9]+)/delete",
        (supplier.PageMaker, "RequestSupplierProductDelete"),
        "POST",
    ),
    (
        "/supplier/([^/]*)/delete",
        (supplier.PageMaker, "RequestSupplierRemove"),
        "POST",
    ),
] + api_urls
