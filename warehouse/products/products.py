#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

import os

import uweb3

from warehouse import basepages
from warehouse.common import model as common_model
from warehouse.orders import model as order_model
from warehouse.suppliers import model as supplier_model
from warehouse.common.decorators import NotExistsErrorCatcher, loggedin
from warehouse.common.helpers import PagedResult
from warehouse.products import forms, model, helpers
import urllib.parse


class PageMaker(basepages.PageMaker):

    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

    @loggedin
    @uweb3.decorators.TemplateParser("products.html")
    def RequestProducts(self, product_form=None):
        """Returns the Products page"""
        supplier = None
        conditions = []
        linkarguments = {}

        products_args = {"conditions": conditions, "order": [("ID", True)]}
        query = ""

        products_method = model.Product.List
        if "query" in self.get and self.get.getfirst("query", False):
            query = self.get.getfirst("query", "")
            linkarguments["query"] = query
            products_args["conditions"] += [
                "ean=%s" % self.connection.EscapeValues(query),
                common_model.NOTDELETED,
            ]

        products = PagedResult(
            self.pagesize,
            self.get.getfirst("page", 1),
            products_method,
            self.connection,
            products_args,
        )

        if not product_form:
            product_form = forms.ProductForm(prefix="product")

        return {
            "supplier": supplier,
            "products": products,
            "linkarguments": urllib.parse.urlencode(linkarguments) or "",
            "query": query,
            "suppliers": list(supplier_model.Supplier.List(self.connection)),
            "product_form": product_form,
        }

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("product.html")
    def RequestProduct(
        self,
        sku,
        product_form=None,
        assemble_form=None,
        stock_form=None,
        assemble_from_part_form=None,
        disassemble_into_parts_form=None,
    ):
        """Returns the product page"""
        product = model.Product.FromSku(self.connection, sku)
        parts = product.parts
        if "unlimitedstock" in self.get:
            stock = list(product.Stock(order=[("dateCreated", True)]))
            stockrows = False
        else:
            stock = list(
                product.Stock(
                    limit=int(self.pagesize),
                    order=[("dateCreated", True)],
                    yield_unlimited_total_first=True,
                )
            )
            stockrows = stock[0]
            stock = stock[1:]

        partsprice = {
            "partstotal": 0,
            "assembly": 0,
            "partcount": 0,
            "assembledtotal": 0,
        }
        for part in list(parts):
            partsprice["partcount"] += part["amount"]
            partsprice["assembly"] += part["assemblycosts"]
            partsprice["partstotal"] += part.subtotal
            partsprice["assembledtotal"] += part.subtotal + part["assemblycosts"]

        possibleparts = model.Product.List(
            self.connection, conditions=[f'ID != {product["ID"]}']
        )

        if not product_form:
            product_form = forms.ProductForm(prefix="product")
            product_form.process(data=product)

        if not assemble_form:
            assemble_form = forms.ProductAssembleFromPartForm(prefix="product-part")
            assemble_form.part.choices = helpers.possibleparts_select_list(
                possibleparts
            )

        factory = forms.get_stock_factory()

        if not stock_form:
            stock_form = factory.get_form("stock_form")
        if not assemble_from_part_form:
            assemble_from_part_form = factory.get_form("assemble_from_part")
        if not disassemble_into_parts_form:
            disassemble_into_parts_form = factory.get_form("disassemble_into_parts")

        product_orders = order_model.OrderProduct.List(
            self.connection,
            conditions=[
                "product_sku = %s" % self.connection.EscapeValues(product["sku"])
            ],
        )

        return {
            "products": product.AssemblyOptions(),
            "parts": parts,
            "partsprice": partsprice,
            "product": product,
            "suppliers": supplier_model.Supplier.List(self.connection),
            "stock": stock,
            "stockrows": stockrows,
            "product_form": product_form,
            "assemble_form": assemble_form,
            "stock_form": stock_form,
            "assemble_from_part_form": assemble_from_part_form,
            "disassemble_into_parts_form": disassemble_into_parts_form,
            "product_orders": product_orders,
        }

    @loggedin
    @uweb3.decorators.checkxsrf
    def RequestProductNew(self):
        """Requests the creation of a new product."""
        form = forms.ProductForm(self.post, prefix="product")

        if not form.validate():
            return self.RequestProducts(product_form=form)

        try:
            product = model.Product.Create(self.connection, form.data)
        except common_model.InvalidNameError:
            return self.RequestInvalidcommand(
                error="Please enter a valid name for the product."
            )
        except model.Product.AlreadyExistError:
            form.sku.errors = ["A product with this SKU already exists."]
            return self.RequestProducts(product_form=form)
        except self.connection.IntegrityError as error:
            self.logger.error("Error: ", error)
            return self.Error("Something went wrong", 200)
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    def RequestProductSave(self, sku):
        """Saves changes to the product"""
        product = model.Product.FromSku(self.connection, sku)
        form = forms.ProductForm(self.post, prefix="product")

        if not form.validate():
            return self.RequestProduct(sku, product_form=form)

        product.update(form.data)
        try:
            product.Save()
        except self.connection.IntegrityError:
            return self.Error("That name was already taken.", 200)

        return uweb3.Redirect(f"/product/{product['sku']}", httpcode=303)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductAssemble(self, sku):
        """Add a new part to an existing product"""
        product = model.Product.FromSku(self.connection, sku)
        possibleparts = model.Product.List(
            self.connection, conditions=[f'ID != {product["ID"]}']
        )
        form = forms.ProductAssembleFromPartForm(self.post, prefix="product-part")
        form.part.choices = helpers.possibleparts_select_list(possibleparts)

        if not form.validate():
            return self.RequestProduct(sku=sku, assemble_form=form)

        try:
            part = model.Product.FromSku(self.connection, form.part.data)
            model.Productpart.Create(
                self.connection,
                {
                    "product": product,
                    "part": part,
                    "amount": form.amount.data,
                    "assemblycosts": form.assemblycosts.data,
                },
            )
        except ValueError:
            return self.RequestInvalidcommand(
                error="Input error, some fields are wrong."
            )
        except self.connection.IntegrityError:
            return self.Error("That part was already assembled in this product!", 200)
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductAssemblySave(self, sku):
        """Update a products assembly by adding, removing or updating part
        references"""
        product = model.Product.FromSku(self.connection, sku)
        deletes = self.post.getfirst("delete", [])
        updates = {
            "amount": self.post.getfirst("amount", []),
            "assemblycosts": self.post.getfirst("assemblycosts", []),
        }

        for mate in product.parts:
            mateid = str(mate["ID"])
            if mateid in deletes:
                mate.Delete()
            else:
                for key in mate:
                    if key in updates and mateid in updates[key]:
                        mate[key] = updates[key][mateid]
                mate.Save()
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductRemove(self, sku):
        """Removes the product"""
        product = model.Product.FromSku(self.connection, sku)
        product.Delete()
        return self.req.Redirect("/", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductStockAdd(self, sku):
        product = model.Product.FromSku(self.connection, sku)

        factory = forms.get_stock_factory(self.post)
        form = factory.get_form("stock_form")

        if not form.validate():
            return self.RequestProduct(sku=sku, stock_form=form)

        try:
            model.Stock.Create(
                self.connection,
                {
                    "product": product,
                    "amount": form.amount.data,
                    "reference": form.reference.data,
                    "piece_price": form.piece_price.data,
                    "lot": form.lot.data,
                },
            )
        except model.AssemblyError as error:
            return self.Error(error)
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductStockAssemble(self, sku):
        """Creates a stock change for the product, either from a new shipment, or
        by assembling/ disassembling a product from its parts."""
        product = model.Product.FromSku(self.connection, sku)

        factory = forms.get_stock_factory(self.post)
        form = factory.get_form("assemble_from_part")

        if not form.validate():
            return self.RequestProduct(sku=sku, assemble_from_part_form=form)

        try:
            product.Assemble(
                **{
                    key: value
                    for key, value in form.data.items()
                    if value is not None
                    and key
                    in (
                        "amount",
                        "reference",
                        "lot",
                    )
                }
            )
        except model.AssemblyError as error:
            return self.Error(error)
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductStockDisassemble(self, sku):
        product = model.Product.FromSku(self.connection, sku)

        factory = forms.get_stock_factory(self.post)
        form = factory.get_form("disassemble_into_parts")

        if not form.validate():
            return self.RequestProduct(sku=sku, disassemble_into_parts_form=form)

        try:
            product.Disassemble(
                **{
                    key: value
                    for key, value in form.data.items()
                    if value is not None
                    and key
                    in (
                        "amount",
                        "reference",
                        "lot",
                    )
                }
            )
        except model.AssemblyError as error:
            return self.Error(error)
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @uweb3.decorators.TemplateParser("gs1.html")
    def RequestGS1(self):
        """Returns the gs1 page"""
        linkarguments = {}
        query = ""
        if "query" in self.get and self.get.getfirst("query", False):
            query = self.get.getfirst("query", "")

            linkarguments["query"] = query
            try:
                product = model.Product.FromGS1(self.connection, query)
                return self.req.Redirect("/product/%s" % product["sku"], httpcode=301)
            except model.Product.NotExistError:
                products = []
        else:
            products = PagedResult(
                self.pagesize,
                self.get.getfirst("page", 1),
                model.Product.List,
                self.connection,
                {"conditions": ["(gs1 is not null)"], "order": [("gs1", False)]},
            )
        return {
            "products": products,
            "linkarguments": urllib.parse.urlencode(linkarguments) or "",
            "query": query,
        }

    @loggedin
    @uweb3.decorators.TemplateParser("ean.html")
    def RequestEAN(self):
        """Returns the EAN page"""
        supplier = None
        conditions = ["(gs1 is not null or ean is not null)"]
        linkarguments = {}

        query = ""
        products_args = {"conditions": conditions, "order": [("ean", False)]}
        products_method = model.Product.List

        if "query" in self.get and self.get.getfirst("query", False):
            query = self.get.getfirst("query", "")
            linkarguments["query"] = query
            products_method = model.Product.EANSearch
            products_args["ean"] = query

        products = PagedResult(
            self.pagesize,
            self.get.getfirst("page", 1),
            products_method,
            self.connection,
            products_args,
        )
        return {
            "supplier": supplier,
            "products": products,
            "linkarguments": urllib.parse.urlencode(linkarguments) or "",
            "query": query,
            "suppliers": list(supplier_model.Supplier.List(self.connection)),
        }

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("product_supplier.html")
    def RequestProductSuppliers(
        self, sku, supplier_product_form=None, couple_form=None
    ):
        product = model.Product.FromSku(self.connection, sku)

        supplier_select_list = helpers.suppliers_select_list(
            supplier_model.Supplier.List(self.connection)
        )
        if not supplier_product_form:
            supplier_product_form = forms.SupplierProduct(
                self.post, prefix="supplier-product"
            )
            supplier_product_form.supplier.choices = supplier_select_list

        if not couple_form:
            couple_form = forms.CoupleSupplierProductForm()
            couple_form.selected_supplier.choices = supplier_select_list

        return dict(
            product=product,
            supplier_product_form=supplier_product_form,
            couple_form=couple_form,
            suppliers=list(
                supplier_model.Supplierproduct.List(
                    self.connection,
                    conditions=[
                        f'product = {product["ID"]}',
                    ],
                )
            ),
        )

    @loggedin
    @NotExistsErrorCatcher
    def RequestAddProductSupplier(self, sku):
        product = model.Product.FromSku(self.connection, sku)

        supplier_product_form = forms.SupplierProduct(
            self.post, prefix="supplier-product"
        )
        supplier_select_list = helpers.suppliers_select_list(
            supplier_model.Supplier.List(self.connection)
        )
        supplier_product_form.supplier.choices = supplier_select_list

        if supplier_product_form.validate():
            supplier_product = {
                "product": product["ID"],
                **supplier_product_form.data,
            }
            supplier_model.Supplierproduct.Create(self.connection, supplier_product)
            return self.req.Redirect(
                f"/product/{product['sku']}/suppliers", httpcode=301
            )
        return self.RequestProductSuppliers(
            sku, supplier_product_form=supplier_product_form
        )

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductRemoveSupplier(self, sku, product_supplier):
        product = model.Product.FromSku(self.connection, sku)
        product_supplier = supplier_model.Supplierproduct.FromPrimary(
            self.connection, product_supplier
        )
        product_supplier.Delete()
        return self.req.Redirect(f"/product/{product['sku']}/suppliers", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    @uweb3.decorators.TemplateParser("prices.html")
    def RequestProductPrices(self, sku, product_vat_form=None):
        product = model.Product.FromSku(self.connection, sku)
        product_price_form = forms.ProductPriceForm(self.post, prefix="product-price")

        if not product_vat_form:
            product_vat_form = forms.ProductVatForm(data=product)

        if self.post and "vat" not in self.post and product_price_form.validate():
            new_product_price = {
                "product": product["ID"],
                **product_price_form.data,
            }
            model.Productprice.Create(self.connection, new_product_price)
            return self.req.Redirect(f"/product/{product['sku']}/prices", httpcode=301)

        return dict(
            product=product,
            product_price_form=product_price_form,
            product_vat_form=product_vat_form,
            product_prices=list(
                model.Productprice.List(
                    self.connection,
                    conditions=f"product = {product['ID']}",
                    order=[("start_range", False)],
                )
            ),
        )

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestSetProductVat(self, sku):
        product = model.Product.FromSku(self.connection, sku)
        product_vat_form = forms.ProductVatForm(self.post)

        if not product_vat_form.validate():
            return self.RequestProductPrices(sku, product_vat_form=product_vat_form)

        product.update(product_vat_form.data)
        product.Save()
        return self.req.Redirect(f'/product/{product["sku"]}/prices', httpcode=303)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestDeleteProductPrice(self, sku, product_price_id):
        product = model.Product.FromSku(self.connection, sku)
        product_price = model.Productprice.FromPrimary(
            self.connection, product_price_id
        )
        product_price.Delete()
        return self.req.Redirect(f"/product/{product['sku']}/prices", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def AttachProductToSupplierProduct(self, sku):
        product = model.Product.FromSku(self.connection, sku)

        couple_form = forms.CoupleSupplierProductForm(self.post)
        couple_form.selected_supplier.choices = helpers.suppliers_select_list(
            supplier_model.Supplier.List(self.connection)
        )
        if couple_form.validate():
            supplier = supplier_model.Supplier.FromPrimary(
                self.connection, couple_form.selected_supplier.data
            )
            # If the Supplierproduct SKU and name are both filled in
            if couple_form.sup_product.data and couple_form.sup_sku.data:
                supplier_product = (
                    supplier_model.Supplierproduct.FromSupplierByNameAndSku(
                        self.connection,
                        int(supplier),
                        couple_form.sup_sku.data,
                        couple_form.sup_product.data,
                    )
                )
            else:
                # Get a Supplierproduct by name only, this will be an issue if the
                # supplier has multiple products with the same name and no SKU is known.
                supplier_product = supplier_model.Supplierproduct.FromSupplierAndName(
                    self.connection, int(supplier), couple_form.sup_product.data
                )

            supplier_product["product"] = int(product)
            supplier_product.Save()
            return self.req.Redirect(f"/product/{sku}/suppliers", httpcode=303)

        return self.RequestProductSuppliers(
            sku,
            couple_form=couple_form,
        )
