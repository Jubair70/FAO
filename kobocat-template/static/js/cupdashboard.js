function getDesiredDate(n) {
    var today = new Date();
    var n_month_before_today = new Date(today);
    n_month_before_today.setMonth((today.getMonth() + 1) - n);
    var dd = n_month_before_today.getDate();
    var mm = n_month_before_today.getMonth() + 1;

    if (dd < 10) {
        dd = '0' + dd
    }
    if (mm < 10) {
        mm = '0' + mm
    }
    var yyyy = n_month_before_today.getFullYear();
    formatted_date = yyyy + '-' + mm + '-' + dd;
    return formatted_date;
}


function generateHHListTable(rowData) {
    var tbody = '';
    for (var i = 0; i < rowData.length; i++) {
        tbody += '<tr><td>' + checkNullVal(rowData[i].hh_id) + '</td><td>' + checkNullVal(rowData[i].hhhead_name) + '</td><td>' + checkNullVal(rowData[i].holding_no) + '</td><td>' + checkNullVal(rowData[i].ward) + '</td><td>' + checkNullVal(rowData[i].hh_phone) + '</td><td>' + checkNullVal(rowData[i].hh_status) + '</td><td><a class="btn red" onclick="getProfile(\'' + rowData[i].hh_id + '\')" role="button">Profile</a></td></tr>';
    }
    $('#hh_table').find('tbody').html(tbody);
}

function getProfile(hh_id) {
    console.log(hh_id)
    $.ajax({
        url: '/household/profile/',
        type: 'POST',
        dataType: 'json',
        data: {'profile_id': hh_id},
        success: function (result) {
            splitData = result.split('@@@@@');
            generateHHProfile(splitData[0]);
            $('#active_hh_id').val(hh_id);
            $('#base_line_btn').attr('href','/cupadmin/forms/Urban_Programme_2016_Baseline_Survey_2/instance/#/'+splitData[1])
            $('#filter-form').hide();
        }

    });
}

function generateHouseHoldMemberLsit(active_hh_id) {
    $.ajax({
        url: '/household/members/',
        type: 'POST',
        dataType: 'json',
        data: {'profile_id': active_hh_id},
        success: function (result) {
            rowData = JSON.parse(result);

            var tbody = '';
            for (var i = 0; i < rowData.length; i++) {
                tbody += '<tr><td>' + (i + 1) + '</td><td>' + checkNullVal(rowData[i].name) + '</td><td>' + checkNullVal(rowData[i].age) + '</td><td>' + checkNullVal(rowData[i].gender) + '</td><td>' + checkNullVal(rowData[i].highest_education_level) + '</td><td>' + checkNullVal(rowData[i].occupation) + '</td><td>' + checkNullVal(rowData[i].disability) + '</td><td></td><td></td><td>' + checkNullVal(rowData[i].member_status) + '</td></tr>';
            }
            $('#hh_member_lsit').find('tbody').html(tbody);
        }
    });
}


function generateSnapShotData(active_hh_id) {
    $.ajax({
        url: '/household/snapshot-data/',
        type: 'POST',
        dataType: 'json',
        data: {'profile_id': active_hh_id},
        success: function (result) {
            rowData = JSON.parse(result);

            var tbody = '';
            for (var i = 0; i < rowData.length; i++) {
                tbody += '<tr><td>' + rowData[i].respondent_name + '</td><td>' + rowData[i].visit_date + '</td><td>' + rowData[i].visit_type + '</td><td>' + rowData[i].sender + '</td><td style="text-align: center;"><button class="btn red">Details</button></td></tr>';
            }
            $('#snapshot_table').find('tbody').html(tbody);
        }
    });
}


function generateHHProfile(rowData) {
    hh_data = JSON.parse(rowData)[0];
    //place data to household profile
    $('#profile_hh_id').html(hh_data.hh_id);
    $('#profile_hh_head').html(hh_data.hhhead_name);
    $('#profile_holding_no').html(hh_data.holding_no);
    $('#profile_mobile_no').html(hh_data.hh_phone);
    $('#profile_asset_grant').html(hh_data.hh_use_asset_name);
    $('#profile_ward').html(hh_data.ward);
    $('#profile_hh_status').html(hh_data.hh_status);
    //transition of tables
    $('#hh_table').fadeOut("slow");
    $('html,body').animate({scrollTop: 0}, 0);
    $('#hh_profile').fadeIn("slow");
    generateHouseHoldMemberLsit(hh_data.hh_id);
    generateSnapShotData(hh_data.hh_id);
    //drawHouseholdMap();
}

function loadHouseholdList() {
    $('#hh_table').fadeIn("slow");
    $('html,body').animate({scrollTop: 0}, 0);
    $('#hh_profile').fadeOut("slow");
    $('#hh_member_lsit').find('tbody').html('');
    $('#filter-form').show();
}


function checkNullVal(field_value) {
    if (field_value == null) {
        return 'N/A';
    } else {
        return field_value;
    }
}


function generate_ward_dropdown(wardData) {
    for (var i = 0; i < wardData.length; i++) {
        $('#f_hh_ward').append($("<option></option>").attr("value", wardData[i].id).text(wardData[i].name));
    }
}

function filterHouseHoldList() {
    var f_hh_id = $('#f_hh_id').val();
    var f_hh_head_name = $('#f_hh_head_name').val();
    var f_hh_ward = $('#f_hh_ward').val();
    var f_hh_mobile = $('#f_hh_mobile').val();

    var params = {};
    if (f_hh_id != '') {
        params['f_hh_id'] = f_hh_id;
    }
    if (f_hh_head_name != '') {
        params['f_hh_head_name'] = f_hh_head_name;
    }
    if (f_hh_ward != 'custom') {
        params['f_hh_ward'] = f_hh_ward;
    }
    if (f_hh_mobile != '') {
        params['f_hh_mobile'] = f_hh_mobile;
    }


    $.ajax({
        url: '/household-filter/',
        type: 'POST',
        dataType: 'json',
        data: params,
        success: function (result) {
            rowData = JSON.parse(result);
            var tbody = '';
            for (var i = 0; i < rowData.length; i++) {
                tbody += '<tr><td>' + checkNullVal(rowData[i].hh_id) + '</td><td>' + checkNullVal(rowData[i].hhhead_name) + '</td><td>' + checkNullVal(rowData[i].holding_no) + '</td><td>' + checkNullVal(rowData[i].ward) + '</td><td>' + checkNullVal(rowData[i].hh_phone) + '</td><td>' + checkNullVal(rowData[i].hh_status) + '</td><td><a class="btn red" onclick="getProfile(\'' + rowData[i].hh_id + '\')" role="button">Profile</a></td></tr>';
            }
            $('#hh_table').find('tbody').html(tbody);
        }
    });
}

function editHouseHold() {
    var active_hh_id = $('#active_hh_id').val();
    createCookie("active_hh_id", active_hh_id);
    window.location.href = '/hhmodule/add_household/'

}