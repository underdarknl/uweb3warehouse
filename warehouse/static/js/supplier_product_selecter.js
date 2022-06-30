(function () {
    "use strict";

    class InputHandler {
        WAIT_INTERVAL = 300;

        constructor() {
            this.timer = null;
            this.supplierProducts = [];
            this.selectedSupplier = document.getElementById("selected_supplier")
            this.inputField = document.getElementById("supplier_product_input");
            this.datalist = document.getElementById(
                "supplier_products_datalist"
            );
            
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
            fetch(`/api/v1/supplier/test?supplier=${this.selectedSupplier.value}&name=${this.inputField.value}`)
                .then((response) => response.json())
                .then((data) => {
                    this.supplierProducts = data;
                    this.updateList();
                })
                .catch((error) => console.log(error));
        }

        updateList() {
            // remove current children
            while (this.datalist.firstChild) {
                this.datalist.removeChild(this.datalist.firstChild);
            }
            this.supplierProducts.forEach((element) => {
                let option = document.createElement("option");
                option.value = element?.name;
                this.datalist.appendChild(option);
            });
            this.inputField.setAttribute("list", "supplier_products_datalist");
        }
    }
    new InputHandler();
})();
