CTFd.plugin.run((_CTFd) => {
    const $ = _CTFd.lib.$;

    // Load available challenge directories
    CTFd.fetch('/api/v1/plugins/ctfd_compose/admin/challenges-dirs', {
        method: 'GET',
    })
    .then(r => r.json())
    .then(res => {
        if (res.success && res.data && res.data.length > 0) {
            const select = $('#compose_dir_select');
            const currentVal = $('#compose_dir').val();

            res.data.forEach(d => {
                select.append($('<option>', {
                    value: d,
                    text: d,
                    selected: (d === currentVal)
                }));
            });

            select.on('change', function() {
                const val = $(this).val();
                if (val) {
                    $('#compose_dir').val(val);
                }
            });
        }
    })
    .catch(err => console.log('Could not load challenge directories', err));

    $('#dynamic_flag').on('change', function() {
        if ($(this).is(':checked')) {
            $('#flag_template_group').show();
        } else {
            $('#flag_template_group').hide();
        }
    });
});
