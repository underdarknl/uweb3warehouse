(function () {
    "use strict";

    class InputHandler {
        WAIT_INTERVAL = 300;

        constructor() {
            this.timer = null;
            this.supplierProducts = [];
            this.selectedSupplier =
                document.getElementById("selected_supplier");
            this.inputField = document.getElementById("supplier_product");
            this.datalist = document.getElementById(
                "supplier_products_datalist"
            );
            this.hiddenSupplierProduct = document.getElementById("sup_product");
            this.hiddenSupplierProductSku = document.getElementById("sup_sku");

            this.inputField.addEventListener("input", (e) => {
                clearTimeout(this.timer);
                if (this.inputField.value) {
                    this.timer = setTimeout(
                        this.populate.bind(this),
                        this.WAIT_INTERVAL
                    );
                }
            });
        }

        populate() {
            fetch(
                `/api/v1/supplier/findproduct?supplier=${this.selectedSupplier.value}&name=${this.inputField.value}`
                )
                .then((response) => {
                    return response.json()})
                .then((data) => {
                    if(data instanceof Array){
                        this.supplierProducts = data;
                        this.updateList();
                    }
                })
                .catch((error) => console.log(error));
                this.updateHiddenFields();
            }

        updateHiddenFields() {
            let selected_option = Array.from(this.datalist.childNodes).find(
                (element) => element.value == this.inputField.value
            );
            if (selected_option) {
                this.hiddenSupplierProduct.value =
                    selected_option.getAttribute("product_name");

                this.hiddenSupplierProductSku.value =
                    selected_option.getAttribute("product_sku");
            }else{
                this.hiddenSupplierProduct.value = "";

                this.hiddenSupplierProductSku.value = "";
            }
        }
        updateList() {
            // remove current children
            while (this.datalist.firstChild) {
                this.datalist.removeChild(this.datalist.firstChild);
            }
            this.supplierProducts.forEach((element) => {
                let option = document.createElement("option");
                if (element?.supplier_sku){
                    option.value = `[${element?.supplier_sku}] ${element?.name}`;
                    option.setAttribute("product_sku", element?.supplier_sku);
                }else{
                    option.value = element?.name;
                }
                option.setAttribute("product_name", element?.name);

                this.datalist.appendChild(option);
            });

            this.inputField.setAttribute("list", "supplier_products_datalist");
        }
    }
    new InputHandler();
})();
