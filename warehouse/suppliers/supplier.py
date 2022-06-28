from io import StringIO
import os

import uweb3

from warehouse import basepages
from warehouse.common import model as common_model
from warehouse.products import model as product_model
from warehouse.common.decorators import NotExistsErrorCatcher, loggedin
from warehouse.common.helpers import PagedResult
from warehouse.suppliers import forms, helpers, model
from warehouse.products.helpers.importers import custom_importers


class PageMaker(basepages.PageMaker):
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("suppliers.html")
    def RequestSuppliers(self, error=None, success=None, supplier_form=None):
        """Returns the suppliers page"""
        if not supplier_form:
            supplier_form = forms.SupplierForm()

        suppliers = None
        query = ""
        if "query" in self.get and self.get.getfirst("query", False):
            suppliermethod = model.Supplier.Search
            supplierarguments = {
                "query": self.get.getfirst("query", ""),
                "order": [("ID", True)],
            }
        else:
            suppliermethod = model.Supplier.List
            supplierarguments = {"order": [("ID", True)]}

        suppliers = PagedResult(
            self.pagesize,
            self.get.getfirst("page", 1),
            suppliermethod,
            self.connection,
            supplierarguments,
        )
        return {
            "suppliers": suppliers,
            "query": query,
            "error": error,
            "success": success,
            "supplier_form": supplier_form,
        }

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("supplier_products.html")
    def RequestSupplierProducts(self, supplierID):
        supplier = model.Supplier.FromPrimary(self.connection, supplierID)
        supplier_products = list(
            model.Supplierproduct.Products(self.connection, supplier)
        )
        supplier_product_form = helpers.get_supplier_product_form(
            self.connection, supplier, self.post
        )
        if self.post and supplier_product_form.validate():
            model.Supplierproduct.Create(self.connection, supplier_product_form.data)
            return self.req.Redirect(f"/supplier/{supplierID}/products", httpcode=301)

        return dict(
            supplier_products=supplier_products,
            supplier=supplier,
            supplier_product_form=supplier_product_form,
        )

    @loggedin
    @NotExistsErrorCatcher
    def RequestSupplierProductDelete(self, supplierID, productID):
        supplier = model.Supplier.FromPrimary(self.connection, supplierID)
        product = model.Supplierproduct.FromPrimary(self.connection, productID)

        if product["supplier"] != supplier:
            return self.Error(
                "Can not delete this product. The product is from another supplier."
            )

        product.Delete()
        return self.req.Redirect(f"/supplier/{supplierID}/products", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestSupplierSave(self, name):
        """Returns the supplier page"""
        supplier = model.Supplier.FromName(self.connection, name)
        supplier_form = forms.SupplierForm(self.post)

        if not supplier_form.validate():
            return self.RequestSupplier(name, supplier_form=supplier_form)

        supplier.update(supplier_form.data)

        try:
            supplier.Save()
        except self.connection.IntegrityError as error:
            if error.args[0] == 1062:
                supplier_form.name.errors = ["Supplier name is already taken."]
                return self.RequestSupplier(name, supplier_form=supplier_form)
            else:
                return self.Error(error)

        return self.req.Redirect(f'/supplier/{supplier["name"]}', httpcode=303)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("supplier.html")
    def RequestSupplier(
        self,
        name,
        supplier_stock_form=None,
        supplier_form=None,
        custom_import_form=None,
        processed_products=None,
        unprocessed_products=None,
        custom_importer=None
    ):
        """Returns the supplier page"""
        supplier = model.Supplier.FromName(self.connection, name)

        if not supplier_form:
            supplier_form = forms.SupplierForm(data=supplier)

        if not supplier_stock_form:
            supplier_stock_form = forms.ImportSupplierStock(
                self.post, prefix=helpers.get_importer_prefix(supplier)
            )

        if not custom_import_form:
            custom_import_form = forms.CustomImporters(self.post)

        return dict(
            supplier=supplier,
            supplier_stock_form=supplier_stock_form,
            supplier_form=supplier_form,
            custom_import_form=custom_import_form,
            processed_products=processed_products,
            unprocessed_products=unprocessed_products,
            custom_importer=custom_importer
        )

    @loggedin
    @uweb3.decorators.checkxsrf
    def RequestSupplierNew(self):
        """Requests the creation of a new supplier."""
        supplier_form = forms.SupplierForm(self.post)

        if not supplier_form.validate():
            return self.RequestSuppliers(supplier_form=supplier_form)

        try:
            supplier = model.Supplier.Create(self.connection, supplier_form.data)
        except common_model.InvalidNameError:
            return self.RequestInvalidcommand(
                error="Please enter a valid name for the supplier."
            )
        except self.connection.IntegrityError:
            return self.Error("Supplier name is already taken.", 200)
        return self.req.Redirect("/supplier/%s" % supplier["name"], httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestSupplierRemove(self, supplier):
        """Removes the supplier"""
        supplier = model.Supplier.FromName(self.connection, supplier)
        supplier.Delete()
        return self.req.Redirect("/suppliers", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    # @uweb3.decorators.TemplateParser("supplier.html")
    def UpdateSupplierStock(self, supplierName):
        supplier = model.Supplier.FromName(self.connection, supplierName)
        prefix = helpers.get_importer_prefix(supplier)
        upload_field = f"{prefix}-fileupload"

        supplier_stock_form = forms.ImportSupplierStock(self.post, prefix=prefix)
        supplier_stock_form.fileupload.data = self.files.get(upload_field)

        if not self.files or not supplier_stock_form.validate():
            if not self.files:
                supplier_stock_form.fileupload.errors = ["No file selected."]
            return self.RequestSupplier(
                name=supplierName, supplier_stock_form=supplier_stock_form
            )

        try:
            (
                processed_products,
                unprocessed_products,
            ) = helpers.import_stock_from_file(
                supplier_stock_form, supplier, self.connection
            )
        except KeyError as exception:
            supplier_stock_form.column_name_mapping.errors = [exception.args[0]]
            supplier_stock_form.column_stock_mapping.errors = [exception.args[0]]
            return self.RequestSupplier(
                name=supplierName, supplier_stock_form=supplier_stock_form
            )
        return self.RequestSupplier(
            name=supplierName,
            supplier_form=forms.SupplierForm(data=supplier),
            supplier_stock_form=forms.ImportSupplierStock(),
            processed_products=processed_products,
            unprocessed_products=unprocessed_products,
        )

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def CustomUpdateSupplierStock(self, supplierName):
        supplier = model.Supplier.FromName(self.connection, supplierName)
        custom_import_form = forms.CustomImporters(self.post)
        custom_import_form.custom_fileupload.data = self.files.get("custom_fileupload")

        if not self.files or not custom_import_form.validate():
            custom_import_form.custom_fileupload.errors = ["No file selected."]
            return self.RequestSupplier(
                name=supplierName, custom_import_form=custom_import_form
            )
        builder = custom_importers.CustomImporters().get_registered_item("solar_city")
        importer = builder(
            StringIO(custom_import_form.custom_fileupload.data[0]["content"])
        )
        importer.Import(model.Supplierproduct.Products(self.connection, supplier))
        return self.RequestSupplier(name=supplierName, custom_importer=importer)
