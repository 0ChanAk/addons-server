/**
 * zCarousel: like jCarouselLite, but good.
 * by potch
 *
 * handles fluid layouts like a champ!
 */

(function($) {

$.fn.zCarousel = function(o) {
    o = $.extend({
        itemsPerPage: 1,
        circular: false
    }, o);

    this.each(function() {
        var $self = $(this),
            $strip = $(".slider", $self),
            $lis = $strip.find(".panel"),
            $prev = $(o.btnPrev),
            $next = $(o.btnNext),
            prop = $("body").hasClass("html-rtl") ? "right" : "left",
            currentPos = 0,
            maxPos = Math.ceil($lis.length / o.itemsPerPage) - 1;

        function render(pos) {
            if (o.circular) {
                currentPos = pos;
                if ($strip.hasClass("noslide")) {
                    currentPos = (pos > maxPos+1) ? 1 : (pos < 1 ? maxPos+1 : pos);
                }
            } else {
                currentPos = Math.min(Math.max(0, pos), maxPos);
            }
            $strip.css(prop, currentPos * -100 + "%");
            $prev.toggleClass("disabled", currentPos == 0 && !o.circular);
            $next.toggleClass("disabled", currentPos == maxPos && !o.circular);

            //wait for paint to clear the class. lame.
            setTimeout(function() {
                $strip.removeClass("noslide");
            }, 0);
        }

        //wire up controls.
        $next.click(_pd(function() {
            render(currentPos+1);
        }));
        $prev.click(_pd(function() {
            render(currentPos-1);
        }));

        // Strip text nodes so inline-block works properly.
        var cn = $strip[0].childNodes;
        for(var i = 0; i < cn.length; i++) {
            if (cn[i].nodeType == 3) {
                $strip[0].removeChild(cn[i]);
            };
        }

        if (o.circular) {
            //pad the beginning with a page from the end vice-versa.
            $strip.prepend($lis.slice(-o.itemsPerPage).clone().addClass("cloned"))
                  .append($lis.slice(0,o.itemsPerPage).clone().addClass("cloned"));
            render(o.itemsPerPage);
            //if we're outside the bounds, disable transitions and snap back to the beginning.
            $strip.bind("transitionend", function() {
                if (currentPos > maxPos+1 || currentPos < 1) {
                    $strip.addClass("noslide");
                    setTimeout(function() {
                        render(currentPos);
                    }, 0);
                }
            });
        } else {
            render(0);
        }
    });
};

})(jQuery);
