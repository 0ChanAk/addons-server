// Hey there! I know how to install apps. Buttons are dumb now.

(function() {
    z.page.on('click', '.button.product', clickHandler);

    function clickHandler(e) {
        e.preventDefault();
        e.stopPropagation();
        var product = $(this).data('product');
        startInstall(product);
    }

    function startInstall(product) {
        if (z.anonymous) {
            localStorage.setItem('toInstall', JSON.stringify(product));
            $(window).trigger('login');
            return;
        }
        if (product.isPurchased || !product.price) {
            install(product);
            return;
        }
        if (product.price) {
            purchase(product);
        }
    }

    function purchase(product) {
        $.when(z.payments.purchase(product))
         .done(purchaseSuccess)
         .fail(purchaseError);
    }

    function purchaseSuccess(product, receipt) {
        // Firefox doesn't successfully fetch the manifest unless I do this.
        setTimeout(function() {
            install(product);
        }, 0);
    }

    function purchaseError(product, msg) {
    }

    function install(product, receipt) {
        var data = {};
        $.post(product.recordUrl).success(function(response) {
            if (response.receipt) {
                data.receipt = response.receipt;
            }
            $.when(apps.install(product, data))
             .done(installSuccess)
             .fail(installError);
        }).error(function(response) {
            throw 'Could not record generate receipt!';
        });
    }

    function installSuccess(product) {
        $(window).trigger('appinstall', product);
    }

    function installError(product) {
        $(window).trigger('appinstallerror', product);
    }

    if (localStorage.getItem('toInstall')) {
        var lsVal = localStorage.getItem('toInstall');
        localStorage.removeItem('toInstall');
        var product = JSON.parse(lsVal);
        startInstall(product);
    }
})();
