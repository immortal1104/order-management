/* =========================================================
static/script.js
v3.1 - Unified Index + Dashboard scripts

Changes in v3.1:
- Updated allOwners names for dashboard charts
- Merged dashboard Chart.js code from template into this file
- Removed need for inline scripts in HTML
========================================================= */

$(document).ready(function () {

/* ---------- INDEX PAGE ---------- */

if ($('#ordersTable').length) {

// Initialise orders list table
let table = $('#ordersTable').DataTable({
retrieve: true,
order: [[8, 'desc']], // default sort by Order Date desc
columnDefs: [
{ targets: [0,1,2,6,7,10,11,12,14,15,16], orderable: false }
],
searching: true,
paging: true,
pageLength: 10,
pagingType: 'simple', // HIGHLIGHT: Only Previous/Next buttons
language: {           // HIGHLIGHT: Bootstrap Icons for pagination
paginate: {
previous: '<i class="bi bi-chevron-left"></i>',
next: '<i class="bi bi-chevron-right"></i>'
}
}
});

// ======= DATE RANGE FILTER JS =======
$.fn.dataTable.ext.search.push(
function(settings, data, dataIndex) {
var dateColIndex = 8; // column index for Order Date
var min = $('#order-date-from').val();
var max = $('#order-date-to').val();

var rowNode = settings.aoData[dataIndex].nTr;
var dateStr = $(rowNode).find('td').eq(dateColIndex).attr('data-order');

if (!dateStr) {
return true; // Show row if date attribute missing
}

var rowDate = new Date(dateStr);
var minDate = min ? new Date(min) : null;
var maxDate = max ? new Date(max) : null;

if ((minDate === null || rowDate >= minDate) && (maxDate === null || rowDate <= maxDate)) {
return true;
}
return false;
}
);

$('#order-date-from, #order-date-to').on('change', function() {
table.draw();
});
// ======= END DATE RANGE FILTER JS =======

// ======= RESET FUNCTION (Add here) =======
    window.resetForm = function() {
      $('#orderForm')[0].reset();
      $('#profit_loss').val('0.00').removeClass('profit loss');
      $('#formTitle').text('Add New Order');
      $('#orderForm').attr('action', '/add');
      $('#order_number').removeClass('is-invalid').removeAttr('aria-invalid').val('');
      $('#order_number').focus();
      $('#order_number').trigger('input');
      $('#order_number').siblings('#order-availability-msg').text('');
    };

// Dashboard → index search trigger
const searchQuery = sessionStorage.getItem('searchQuery');
if (searchQuery) {
table.search(searchQuery).draw();
sessionStorage.removeItem('searchQuery');
}

setTimeout(function() {
$('.alert').not('.emi-alert').fadeTo(500, 0).slideUp(500, function(){
$(this).remove();
});
}, 2000);

// Dashboard → index edit trigger
const editOrderData = sessionStorage.getItem('editOrderData');
if (editOrderData) {
try {
const order = JSON.parse(editOrderData);
fillEditForm(order); // fill form fields
toggleView('form'); // switch to form view
} catch(e) {
console.error("Invalid editOrderData", e);
}
sessionStorage.removeItem('editOrderData');
}

// Delivery status toggle on index table
$(document).on('change', '.delivery-status-toggle', function() {
const orderNo = $(this).data('order');
const status = $(this).is(':checked') ? 1 : 0;
$.ajax({
url: '/update_delivery_status',
method: 'POST',
contentType: 'application/json',
data: JSON.stringify({ order_number: orderNo, delivery_status: status }),
success: function (res) {
if (!res.success) {
alert('Failed to update delivery status');
}
}
});
});

}

/* ---------- DASHBOARD PAGE ---------- */

if ($('#monthlyChart').length) {
// ✅ Updated owner names here
const allOwners = ['GS', 'GSW', 'DS', 'BS', 'NS', 'BK', 'JK', 'Others'];
// Ensure all owners exist in objects, even with zero value
let monthlyData = Object.assign(...allOwners.map(o => ({[o]: 0})), window.monthlyData || {});
let yearlyData = Object.assign(...allOwners.map(o => ({[o]: 0})), window.yearlyData || {});

// 📊 Monthly Bar Chart
new Chart(document.getElementById('monthlyChart'), {
type:'doughnut',
data:{
labels:Object.keys(monthlyData),
datasets:[{
label:'Monthly Spend (₹)',
data:Object.values(monthlyData),
backgroundColor:Object.keys(monthlyData).map(l => l === 'Others' ? '#6c757d' : '#0d6efd'),
borderRadius:6
}]
},
options:{
indexAxis:'y', responsive:true,
plugins:{ legend:{ display:false }},
scales:{
x:{ beginAtZero:true, ticks:{ font:{ size:10 }}},
y:{ ticks:{ font:{ size:10 }}}
}
}
});

// 📆 Yearly Bar Chart
new Chart(document.getElementById('yearlyChart'), {
type:'doughnut',
data:{
labels:Object.keys(yearlyData),
datasets:[{
label:'Yearly Spend (₹)',
data:Object.values(yearlyData),
backgroundColor:Object.keys(yearlyData).map(l => l === 'Others' ? '#6c757d' : '#0d6efd'),
borderRadius:6
}]
},
options:{
indexAxis:'y', responsive:true,
plugins:{ legend:{ display:false }},
scales:{
x:{ beginAtZero:true, ticks:{ font:{ size:10 }}},
y:{ ticks:{ font:{ size:10 }}}
}
}
});

// Delivery status toggle on dashboard tables
$(document).on('change', '.delivery-status-toggle', function () {
const orderNo = $(this).data('order');
const status = $(this).is(':checked') ? 1 : 0;
$.ajax({
url: '/update_delivery_status',
method: 'POST',
contentType: 'application/json',
data: JSON.stringify({ order_number: orderNo, delivery_status: status }),
success: res => { if (!res.success) alert('Failed to update'); else location.reload(); }
});
});

// Mark cash pending as received
$(document).on('change', '.mark-cash', function () {
const orderNo = $(this).data('order');
if ($(this).is(':checked')) {
$.ajax({
url: '/mark_cash_received',
type: 'POST',
contentType: 'application/json',
data: JSON.stringify({ order_number: orderNo }),
success: res => { if (res.success) location.reload(); else alert("Failed to update."); }
});
}
});

}

});

/* =========================================================
COMMON FUNCTIONS (used on Index & Dashboard)
========================================================= */

// Toggle between form and table view
function toggleView(view) {
$('#formSection').toggle(view === 'form');
$('#tableSection').toggle(view === 'table');
}

// Calculate profit/loss in form
function calcProfitLoss(){
var purchase = parseFloat($('#purchase').val())||0;
var sell = parseFloat($('#sell').val())||0;
var pl = sell - purchase;
$('#profit_loss').val(pl.toFixed(2));
// 🔹 Remove any prev colour class first
$('#profit_loss').removeClass('profit loss');
if (pl > 0) {
$('#profit_loss').addClass('profit');
} else if (pl < 0) {
$('#profit_loss').addClass('loss');
}
}

// Fill edit form with given order object on index
function fillEditForm(order){
toggleView('form');
$('#formTitle').text('Edit Order: '+order.order_number);
for(var key in order){
if($('#'+key).length){
if($('#'+key).attr('type')==='checkbox'){
$('#'+key).prop('checked', order[key]==1);
}else{
$('#'+key).val(order[key]);
}
}
}
$('#orderForm').attr('action','/edit/'+order.order_number);
// 🔹 New: update profit/loss colour immediately
calcProfitLoss();
}

// AJAX check if order number exists
function checkOrderAvailability() {
const orderNo = $('#order_number').val().trim();
const msgEl = $('#order-availability-msg');
if (!orderNo) {
msgEl.text('');
return;
}
$.ajax({
url: "/check_order_exists",
method: "POST",
contentType: "application/json",
data: JSON.stringify({ order_number: orderNo }),
success: function (data) {
if (data.exists) msgEl.text('⚠️ Order number already exists!');
else msgEl.text('');
}
});
}

// Dashboard → Index "View" click
function viewOrder(orderNo) {
sessionStorage.setItem('searchQuery', orderNo);
window.location.href = '/';
}

// Dashboard → Index "Edit" click
function editOrder(orderObj) {
sessionStorage.setItem('editOrderData', JSON.stringify(orderObj));
window.location.href = '/';
}
