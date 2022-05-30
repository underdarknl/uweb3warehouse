# standard modules
from io import StringIO

# uweb modules
import uweb3

# project modules
from base import model
from base.decorators import NotExistsErrorCatcher
from base.helpers import PagedResult
from base.libs import stock_importer


class PageMaker:
    @uweb3.decorators.loggedin
    @uweb3.decorators.TemplateParser("suppliers.html")
    def RequestSuppliers(self, error=None, success=None):
        """Returns the suppliers page"""
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
        }

    @uweb3.decorators.loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestSupplierSave(self, name):
        """Returns the supplier page"""
        supplier = model.Supplier.FromName(self.connection, name)
        for key in (
            "name",
            "website",
            "telephone",
            "contact_person",
            "email_address",
            "gscode",
        ):
            supplier[key] = self.post.getfirst(key, None)
        supplier.Save()
        return self.RequestSuppliers(success="Changes saved.")

    @uweb3.decorators.loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("supplier.html")
    def RequestSupplier(self, name):
        """Returns the supplier page"""
        return {"supplier": model.Supplier.FromName(self.connection, name)}

    @uweb3.decorators.loggedin
    @uweb3.decorators.checkxsrf
    def RequestSupplierNew(self):
        """Requests the creation of a new supplier."""
        try:
            supplier = model.Supplier.Create(
                self.connection,
                {
                    "name": self.post.getfirst("name", "").replace(" ", "_"),
                    "website": self.post.getfirst("website")
                    if "website" in self.post
                    else None,
                    "telephone": self.post.getfirst("telephone")
                    if "telephone" in self.post
                    else None,
                    "contact_person": self.post.getfirst("contact_person")
                    if "contact_person" in self.post
                    else None,
                    "email_address": self.post.getfirst("email_address")
                    if "email_address" in self.post
                    else None,
                    "gscode": self.post.getfirst("gscode")
                    if "gscode" in self.post
                    else None,
                },
            )
        except ValueError:
            return self.RequestInvalidcommand(
                error="Input error, some fields are wrong."
            )
        except model.InvalidNameError:
            return self.RequestInvalidcommand(
                error="Please enter a valid name for the supplier."
            )
        except self.connection.IntegrityError:
            return self.Error("That name was already taken, go back, try again!", 200)
        return self.req.Redirect("/supplier/%s" % supplier["name"], httpcode=301)

    @uweb3.decorators.loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestSupplierRemove(self, supplier):
        """Removes the supplier"""
        supplier = model.Supplier.FromName(self.connection, supplier)
        supplier.Delete()
        return self.req.Redirect("/suppliers", httpcode=301)

    @uweb3.decorators.loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    @uweb3.decorators.TemplateParser("supplier.html")
    def UpdateSupplierStock(self, supplier):
        if not self.files or not self.files.get("fileupload"):
            return
        supplier = model.Supplier.FromName(self.connection, supplier)
        mapping = {"amount": "Op voorraad", "name": "Type"}
        # Get the only file in the request
        file = self.files["fileupload"][0]
        # Pass the content of the file to a StringIO object
        test = StringIO(file["content"])
        # Create a parser that looks for specific columns
        parser = stock_importer.StockParser(
            test,
            ("Fabrikant", "Type", "Op voorraad", "Prijs per stuk"),
            ("Type",),
        )
        # Parse the file in an attempt to find the products
        products = list(
            model.Product.List(
                self.connection, conditions=[f'supplier = {supplier["ID"]}']
            )
        )
        importer = stock_importer.StockImporter(
            self.connection,
            mapping,
        )
        importer.Import(
            parser.Parse(),
            products,
        )
        return {
            "supplier": supplier,
            "processed_products": importer.processed_products,
            "unprocessed_products": importer.unprocessed_products,
        }
