 $(document).on("click", "#copy_last_session", function() {
    $('#create_of_update_form_wrapper').hide();
    $('#last_form_wrapper').show();
});


$(document).on("change", "#id_film", function() {
    /**
    * Auto set dimension if selected film has one dimension and
    * disable dimensions without active agreement
    */
    $('#id_dimension input').prop( "checked", false);

    var dimension_ids = $(this).find("option:selected" ).data('film-dimensions').split(',');

    $('#id_dimension').find("input").prop('disabled', true);
    $('#id_dimension').find("input[value='" + dimension_ids.join("'],input[value='") + "']").prop('disabled', false);

    if(dimension_ids.length === 2){
        $('#id_dimension').find("[value='" + dimension_ids[0] + "']").prop( "checked", true );
    }
});

$(window).on('load', function () {

    $(window).scrollTop($('#create_of_update_form_wrapper').offset().top);

    $("#id_date, #id_change_date_to").datepicker({
        dateFormat: "dd/mm/yy",
        maxDate: 0,
        minDate: -30
    })
});

function add_subtotal_row(row, film_name, dimension, invitations_count_sum, viewers_count_sum, gross_yield_sum) {
    row.after(
        '<tr class="subtotal"><td class="cinema_hall" colspan="4" >' +
        film_name + ' (' + dimension + ')</td>' +
        '<td class="invitations_count">' + invitations_count_sum + '</td>' +
        '<td class="viewers_count">' + viewers_count_sum + '</td>' +
        '<td class="gross_yield">' + gross_yield_sum.toLocaleString() + '</td>' +
        '<td></td>'.repeat(6) +
        '</tr>'
    )
}

 $(document).ready(function(){
    /**
    * Add subtotal rows to sessions table
    */

    if (window.location.href.indexOf('order-by-time') > 0){
        return;
    }

    var previous_row_film_name = undefined;
    var previous_row_dimension = undefined;
    var prev_row = undefined;
    var viewers_count_sum = 0;
    var gross_yield_sum = 0;
    var invitations_count_sum = 0;
    var tables_rows = $('#session_list_table_wrapper').find('table tbody tr:not(.subtotal)');
    tables_rows.each(function(index) {
        var film_name_td = $(this).find('.film');

        if (film_name_td.length === 0) { return false }

        var film_name = film_name_td.html();
        var dimension  = $(this).find('.dimension').html();
        var invitations_count = parseInt($(this).find('.invitations_count').html());
        var viewers_count = parseInt($(this).find('.viewers_count').html());
        var gross_yield = parseFloat($(this).find('.gross_yield').html().replace(',', ''));

        if ((previous_row_film_name && film_name !== previous_row_film_name) || (previous_row_dimension && dimension !== previous_row_dimension)){
            add_subtotal_row(prev_row, previous_row_film_name, previous_row_dimension,
                             invitations_count_sum, viewers_count_sum, gross_yield_sum);

            invitations_count_sum = 0;
            viewers_count_sum = 0;
            gross_yield_sum = 0;
        }

        if (index == tables_rows.length - 1){
             add_subtotal_row($(this), film_name, dimension,
                              invitations_count_sum + invitations_count,
                              viewers_count_sum + viewers_count,
                              gross_yield_sum + gross_yield);
        }

        invitations_count_sum += invitations_count;
        viewers_count_sum += viewers_count;
        gross_yield_sum += gross_yield;

        previous_row_film_name = film_name;
        previous_row_dimension = dimension;
        prev_row = $(this);

    });
});
