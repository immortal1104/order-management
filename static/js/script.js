/* =========================================================
static/script.js

v3.2 - Unified Index + Dashboard scripts (with Profit Fix)

Changes in v3.2:
- Fixed profit/loss calculation (auto updates on input change)
- Removed duplicate confirmDelete definition
- Added error handler for order availability AJAX
- Cleaned Chart.js config (removed unused scales for doughnut)
========================================================= */

$(document).ready(function () {
    /* ---------- INDEX PAGE ---------- */
    if ($('#ordersTable').length) {
        // Initialise orders table
        let table = $('#ordersTable').DataTable({
            retrieve: true,
            order: [[8, 'desc']],
            deferRender: true,
            columnDefs: [
                { targets: [0,1,2,6,7,10,11,12,14,15,16], orderable: false }
            ],
            searching: true,
            paging: true,
            pageLength: 10,
            pagingType: 'simple',
            language: {
                paginate: {
                    previous: '<i class="bi bi-chevron-left"></i>',
                    next: '<i class="bi bi-chevron-right"></i>'
                }
            }
        });

        // Date range filter
        $.fn.dataTable.ext.search.push(
            function (settings, data, dataIndex) {
                var min = $('#order-date-from').val();
                var max = $('#order-date-to').val();
                var dateStr = data[8]; // Order Date column
                if (!dateStr) return true;
                var date = new Date(dateStr);
                if ((min === "" || date >= new Date(min)) && (max === "" || date <= new Date(max))) {
                    return true;
                }
                return false;
            }
        );

        $('#order-date-from, #order-date-to').change(function () {
            table.draw();
        });

        // Reset form
        window.resetForm = function () {
            $('#orderForm')[0].reset();
            $('#profit_loss').val('0.00').removeClass('profit loss');
            $('#formTitle').text('Add New Order');
            $('#orderForm').attr('action', '/add');
            $('#order_number').removeClass('is-invalid').removeAttr('aria-invalid').val('');
            $('#order_number').focus();
            $('#order_number').trigger('input');
            $('#order-availability-msg').text('');
        }

        // Trigger search if any
        const searchQuery = sessionStorage.getItem('searchQuery');
        if (searchQuery) {
            table.search(searchQuery).draw();
            sessionStorage.removeItem('searchQuery');
        }

        // Auto dismiss alerts
        setTimeout(function () {
            $('.alert').not('.emi-alert').fadeTo(500, 0).slideUp(500, function () {
                $(this).remove();
            });
        }, 2000);

        // Load order data in form for edit
        const editData = sessionStorage.getItem('editOrderData');
        if (editData && editData !== "null") {
            try {
                var order = JSON.parse(editData);
                fillEditForm(order);
                toggleView('form');
            } catch (e) { console.error(e); }
            sessionStorage.removeItem('editOrderData');
        }

        // Delivery status toggle
        $(document).on('change', '.delivery-status-toggle', function () {
            var orderNo = $(this).data('order');
            var status = $(this).is(':checked') ? 1 : 0;
            $.ajax({
                url: '/update_delivery_status',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ order_number: orderNo, delivery_status: status }),
                success: function (res) {
                    if (!res.success) alert('Failed to update status');
                }
            });
        });

        // Delete confirmation - Delegated event handler
        window.confirmDelete = function (orderNumber) {
            if (confirm("Are you sure you want to delete order #" + orderNumber + "?")) {
                document.getElementById('deleteForm' + orderNumber).submit();
            }
        }
    }

    /* ---------- DASHBOARD PAGE ---------- */
    if ($('#monthlyChart').length) {
        const allOwners = ['GS', 'GSW', 'DS', 'BS', 'NS', 'BK', 'JK', 'Others'];
        let monthlyData = Object.assign(...allOwners.map(o => ({ [o]: 0 })), window.monthlyData || {});
        let yearlyData = Object.assign(...allOwners.map(o => ({ [o]: 0 })), window.yearlyData || {});

        new Chart($('#monthlyChart'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(monthlyData),
                datasets: [{
                    label: 'Monthly Spend (₹)',
                    data: Object.values(monthlyData),
                    backgroundColor: Object.keys(monthlyData).map(l => l === 'Others' ? '#6c757d' : '#0d6efd'),
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } }
            }
        });

        new Chart($('#yearlyChart'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(yearlyData),
                datasets: [{
                    label: 'Yearly Spend (₹)',
                    data: Object.values(yearlyData),
                    backgroundColor: Object.keys(yearlyData).map(l => l === 'Others' ? '#6c757d' : '#0d6efd'),
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } }
            }
        });

        // Delivery status toggle in dashboard
        $(document).on('change', '.delivery-status-toggle', function () {
            var orderNo = $(this).data('order');
            var status = $(this).is(':checked') ? 1 : 0;
            $.ajax({
                url: '/update_delivery_status',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ order_number: orderNo, delivery_status: status }),
                success: function (res) {
                    if (!res.success) alert('Failed to update status');
                    else location.reload();
                }
            });
        });

        // Mark cash received toggle
        $(document).on('change', '.mark-cash', function () {
            var orderNo = $(this).data('order');
            if ($(this).is(':checked')) {
                $.ajax({
                    url: '/mark_cash_received',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ order_number: orderNo }),
                    success: function (res) {
                        if (res.success) location.reload();
                        else alert('Failed to mark cash received.');
                    }
                });
            }
        });
    }

    // 🔥 FIX: Auto calculate profit/loss when purchase/sell changes
    $('#purchase, #sell').on('input', calcProfit);
});

/* COMMON FUNCTIONS */

// Toggle between form and table
function toggleView(view) {
    $('#formSection').toggle(view === 'form');
    $('#tableSection').toggle(view === 'table');
}

// Calculate profit/loss with color
function calcProfit() {
    var purchase = parseFloat($('#purchase').val()) || 0;
    var sell = parseFloat($('#sell').val()) || 0;
    var pl = sell - purchase;
    $('#profit_loss').val(pl.toFixed(2)).removeClass('profit loss');
    if (pl > 0) $('#profit_loss').addClass('profit');
    else if (pl < 0) $('#profit_loss').addClass('loss');
}

// Populate form with order data for editing
function fillEditForm(order) {
    toggleView('form');
    $('#formTitle').text('Edit Order: ' + order.order_number);
    for (var key in order) {
        let el = $('#' + key);
        if (!el.length) continue;
        if (el.attr('type') === 'checkbox') el.prop('checked', order[key] == 1);
        else el.val(order[key]);
    }
    $('#orderForm').attr('action', '/edit/' + order.order_number);
    calcProfit();
}

// Check order number availability with AJAX
function checkOrderAvailability() {
    var orderNo = $('#order_number').val().trim();
    var msgEl = $('#order-availability-msg');
    if (!orderNo) {
        msgEl.text('');
        return;
    }
    $.ajax({
        url: '/check_order_exists',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ order_number: orderNo }),
        success: function (data) {
            if (data.exists) msgEl.text('⚠️ Order number already exists!');
            else msgEl.text('');
        },
        error: function () {
            msgEl.text('⚠️ Could not check order number.');
        }
    });
}

// Navigation to view order details
function viewOrder(orderNo) {
    sessionStorage.setItem('searchQuery', orderNo);
    window.location.href = '/';
}

// Navigation to edit order
function editOrder(orderObj) {
    sessionStorage.setItem('editOrderData', JSON.stringify(orderObj));
    window.location.href = '/';
}

// Confirm delete and submit form
function confirmDelete(orderNumber) {
    if (confirm("Are you sure you want to delete order #" + orderNumber + "?")) {
        document.getElementById('deleteForm' + orderNumber).submit();
    }
}
