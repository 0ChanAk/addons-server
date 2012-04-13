function slider() {
    var $el = $(this),
        $ul = $('ul', $el).eq(0),
        startX,
        newX,
        prevX,
        currentX = 0;
        lastMove = 0;
        contentWidth = 0,
        sliderWidth = $el.outerWidth();
    $ul.find('li').each(function() {
        contentWidth += $(this).outerWidth();
    });
    var maxScroll = sliderWidth - contentWidth;
    $el.find('img').bind('mousedown mouseup mousemove', function(e) {
        e.preventDefault();
    })
    $el.bind('touchstart', function(e) {
        // e.preventDefault();
        var oe = e.originalEvent;
        startX = oe.touches[0].pageX;
        $ul.addClass('panning');
        $ul.css('-webkit-transition-timing', null)
        lastMove = oe.timeStamp;
    });
    $el.bind('touchmove', function(e) {
        // e.preventDefault();
        var oe = e.originalEvent;
        var eX = oe.targetTouches[0].pageX;
        prevX = newX;
        newX = currentX + (eX - startX);
        $ul.css('-moz-transform', 'translate3d(' + newX + 'px, 0, 0)');
        $ul.css('-webkit-transform', 'translate3d(' + newX + 'px, 0, 0)');
        lastMove = oe.timeStamp;
    });
    $el.bind('touchend', function(e) {
        var oe = e.originalEvent;
        var eX = oe.changedTouches[0].pageX;
        newX = currentX + (eX - startX);
        var dist = newX - prevX;
        if (Math.abs(startX - newX) < 10) {
            return true;
        }
        e.preventDefault();
        var time = oe.timeStamp - lastMove;
        var finalX = newX + (dist * 350 / time);
        // if (finalX > 0 || finalX < contentWidth) {
        //     var overShoot = Math.abs(finalX > 0 ? finalX : (contentWidth - finalX));
        //     var after_finalX = Math.min(Math.max(finalX, maxScroll), 0);
        //     $ul.one('webkitTransitionEnd', function() {
        //         $ul.css('-webkit-transform', 'translate3d(' + after_finalX + 'px, 0, 0)');
        //         currentX = after_finalX;
        //     });
        // } else {
            finalX = Math.min(Math.max(finalX, maxScroll), 0);
        // }
        currentX = finalX;
        $ul.removeClass('panning');
        $ul.css('-moz-transform', 'translate3d(' + currentX + 'px, 0, 0)');
        $ul.css('-webkit-transform', 'translate3d(' + currentX + 'px, 0, 0)');
    });
    $(window).bind('saferesize', function() {
        sliderWidth = $el.outerWidth();
        maxScroll = sliderWidth - contentWidth;
    });
}

z.page.on('fragmentloaded', function() {
    // $('.slider').each(slider);
});

$('.slider').each(function() {
    var $this = $(this),
        $ul = $this.find('ul'),
        $a = $ul.find('a');
    $this.hover(function(e) {
        $ul.addClass('moving-left');
        // e.clientX > ($this.width() / 2)
    });
    $this.mouseout(function() {
        $a.removeClass('frozen');
        $ul.addClass('done');
    });
    $a.hover(_.throttle(function(e) {
        $(this).addClass('frozen');
        $ul.addClass('done');
    }, 250));
    $a.mouseout(_.throttle(function(e) {
        $(this).removeClass('frozen');
        $ul.removeClass('done');
    }, 250));
});
