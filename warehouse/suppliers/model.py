#!/usr/bin/python3
"""Database abstraction model for the warehouse."""

__author__ = "Jan Klopper <janklopper@underdark.nl>"
__version__ = "1.0"

# standard modules
import datetime
import re

import pytz

# Custom modules
from uweb3 import model

from warehouse.common import model as common_model


class Supplierproduct(model.Record):
    """Used for mapping a product to a supplier product."""

    @classmethod
    def List(cls, connection, conditions=[], *args, **kwargs):
        """Returns the Suppliers filterd on not deleted"""
        return super().List(
            connection,
            conditions=[common_model.NOTDELETED] + conditions,
            *args,
            **kwargs,
        )

    @classmethod
    def Products(cls, connection, supplier):
        return cls.List(
            connection,
            conditions=[
                f"supplier={supplier['ID']}",
            ],
        )

    @classmethod
    def NameLike(cls, connection, supplierID, name):
        name = f"%{str(name)}%"
        return cls.List(
            connection,
            conditions=[
                "supplier = %s" % connection.EscapeValues(supplierID),
                "name like %s" % connection.EscapeValues(name),
                "product is null",
            ],
            fields=(
                "ID",
                "name",
                "supplier_sku",
            ),
            limit=10,
        )

    @classmethod
    def FromSupplierByNameAndSku(
        cls, connection, supplier_id, product_sku, product_name
    ):
        with connection as cursor:
            supplier_product = cursor.Execute(
                f"""SELECT *
                FROM supplierproduct
                WHERE supplier={connection.EscapeValues(supplier_id)}
                AND supplier_sku={connection.EscapeValues(product_sku)}
                AND name={connection.EscapeValues(product_name)}
                LIMIT 1"""
            )
        if not supplier_product:
            raise cls.NotExistError(
                "There is no supplier product with name "
                + "{product_name!r} and sku {product_sku!r} "
                + "for supplier {supplier_id}"
            )
        return cls(connection, supplier_product[0])

    @classmethod
    def FromSupplierAndName(cls, connection, supplier_id, product_name):
        with connection as cursor:
            supplier_product = cursor.Execute(
                f"""SELECT *
                FROM supplierproduct
                WHERE supplier={connection.EscapeValues(supplier_id)}
                AND name={connection.EscapeValues(product_name)} 
                LIMIT 1"""
            )
        if not supplier_product:
            raise cls.NotExistError(
                "There is no supplier product with name "
                + "{product_name!r} "
                + "for supplier {supplier_id}"
            )
        return cls(connection, supplier_product[0])

    def Delete(self):
        """Overwrites the default Delete and sets the dateDeleted datetime instead"""
        self["dateDeleted"] = str(pytz.utc.localize(datetime.datetime.utcnow()))[0:19]
        self.Save()


class Supplier(model.Record):
    """Provides a model abstraction for the Supplier table"""

    @classmethod
    def List(cls, connection, conditions=[], *args, **kwargs):
        """Returns the Suppliers filterd on not deleted"""
        return super().List(
            connection,
            conditions=[common_model.NOTDELETED] + conditions,
            *args,
            **kwargs,
        )

    @classmethod
    def Search(cls, connection, query=None, conditions=None, order=None, **kwargs):
        """Returns the suppliers matching the search

        Arguments:
        @ connection: sqltalk.connection
          Database connection to use.
        % query: str
          Filters on name
        """
        if not conditions:
            conditions = []

        if not order:
            order = []

        return cls.List(
            connection,
            conditions=conditions
            + ['name like "%%%s%%"' % connection.EscapeValues(query)[1:-1]]
            + conditions,
            order=order + [("ID", True)],
            **kwargs,
        )

    @classmethod
    def FromName(cls, connection, name, conditions=[]):
        """Returns the supplier of the given common name.

        Arguments:
          @ connection: sqltalk.connection
            Database connection to use.
          @ name: str
            The common name of the collection.

        Raises:
          NotExistError:
            The given supplier name does not exist.

        Returns:
          Supplier: supplier abstraction class.
        """
        safe_name = connection.EscapeValues(name)
        with connection as cursor:
            supplier = cursor.Select(
                table=cls.TableName(),
                conditions=["name=%s" % safe_name, common_model.NOTDELETED]
                + conditions,
            )
        if not supplier:
            raise cls.NotExistError("There is no supplier with common name %r" % name)
        return cls(connection, supplier[0])

    def Delete(self):
        """Overwrites the default Delete and sets the dateDeleted datetime instead"""
        self["dateDeleted"] = str(pytz.utc.localize(datetime.datetime.utcnow()))[0:19]
        self.Save()

    def _PreCreate(self, cursor):
        super()._PreCreate(cursor)
        if self["gscode"]:
            self["gscode"] = self["gscode"][:10]
        if self["name"]:
            self["name"] = re.search(
                "([\w\-_\.,]+)", self["name"].replace(" ", "_")  # noqa W605
            ).groups()[0][:45]
        if not self["name"]:
            raise common_model.InvalidNameError("Provide a valid name")

    def _PreSave(self, cursor):
        super()._PreSave(cursor)
        if self["gscode"]:
            self["gscode"] = self["gscode"][:10]
        if self["name"]:
            self["name"] = re.search(
                "([\w\-_\.,]+)", self["name"].replace(" ", "_")  # noqa W605
            ).groups()[0][:45]
        if not self["name"]:
            raise common_model.InvalidNameError("Provide a valid name")
