Gratipay.table = (function() {
    function init() {
        $('table[data-url]').each(initTable);
    }

    function initTable(i, table) {
        var dataUrl = $(table).data('url');
        jQuery.get(dataUrl).success(function(data) {
            $('.loading-indicator').remove();
            var rows = renderRows(data.members);
            $('tbody', table).html(rows);
        });
    }


    // Render Rows
    // ===========

    function renderRows(records) {
        nrecords = records.length;
        var rows = [];

        for (var i=0, len=records.length; i<len; i++) {
            var record = records[i];
            rows.push(Gratipay.jsonml(
                [ 'tr'
                , ['td', {'class': 'n'}, nrecords-i]
                , ['td', ['a', {'href': '/'+record.username+'/'}, record.username]]
                 ]
            ));
        }
        return rows;
    }


    // Export
    // ======

    return {init: init};
})();
