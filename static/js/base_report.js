jQuery.expr[":"].icontains = jQuery.expr.createPseudo(function(arg) {
    return function( elem ) {
        return jQuery(elem).text().toUpperCase().indexOf(arg.toUpperCase()) >= 0;
    };
});


$(document).on('input', '.filter-options', function(){
    var query = $(this).val(),
        $ul = $(this).siblings('ul');

    if (!query.length) {
        $ul.find('label').show();
    } else {
        $ul.find('label:not(:icontains(' + query + '))').hide();
        $ul.find('label:icontains(' + query + ')').show();
    }
});

var loader = $('#loader').hide();
$(document)
    .ajaxStart(function () {
        loader.show();
    })
    .ajaxStop(function () {
        loader.hide();
    });


$(document).on('click', '.export-data-btn', function () {

    var export_form = $(this).closest("form");

    // add params from filter-form to export form before submit
    export_form.find("input[from_form='filter-form']" ).remove();
    $.each($('#filter-form').serializeArray(), function() {
        var input = $("<input>", {
            type: "hidden",
            name: this.name,
            value: this.value,
            from_form: "filter-form" }
        );

        export_form.append(input);
    });

    export_form.submit();
});
