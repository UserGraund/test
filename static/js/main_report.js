$(window).on('load', function() {
    $( "#id_date_range_0, #id_date_range_1" ).datepicker({
        dateFormat: "dd/mm/yy"
    })
});

function refresh_table_and_update_url(data, status, xhr){
    $('#report-table').html(data);
    window.history.pushState("", "", xhr.getResponseHeader('Location'));
    $('html, body').animate({
        scrollTop: 30
    }, 400);
}

function handle_error(jqXHR) {
    console.log('Something went wrong. HTTP status code:', jqXHR.status);
}

$(document).on("click", ".filter-data", function() {
    var $form = $('#filter-form');
    var form_data = $form.find(" :input")
            .filter(function(index, element) {
                return $(element).val() != "";
            })
            .serialize();

    $.ajax({
        url: $form.attr('action'),
        data: form_data,
        success: refresh_table_and_update_url,
        error: handle_error
    });
});

$(document).on("click", ".pagination a", function(event) {
    event.preventDefault();
    $.ajax({
        url: $(this).attr('href'),
        success: refresh_table_and_update_url,
        error: handle_error
    });
});

$(window).scroll(function() {
    var float_submit = $('#float-submit');
    float_submit.css('left', $('.container').css('marginLeft') + 'px');

    if ($(this).scrollTop()) {
        float_submit.fadeIn();
    } else {
        float_submit.fadeOut();
    }
});


$(document).on('change', '#id_date_range_0,#id_date_range_1', function () {
    var date_from_list = $('#id_date_range_0').val().split('/'),
        date_from = new Date(date_from_list[2], date_from_list[1] - 1, date_from_list[0]),
        date_to_list = $('#id_date_range_1').val().split('/'),
        date_to = new Date(date_to_list[2], date_to_list[1] - 1, date_to_list[0]);

    if (date_to.getTime() < date_from.getTime()) {
        $('#id_date_range_1').val("")
    }

    $('#filter-form').submit();
});


$(document).on('change', '#export-form #id_export_group_by', function () {
    var group_by = $(this).val();

    if (group_by) {
        $('#flat_columns_wrapper').hide();
        $('#grouped_columns_wrapper').show();
    } else {
        $('#grouped_columns_wrapper').hide();
        $('#flat_columns_wrapper').show();
    }
});


