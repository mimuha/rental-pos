(function($) {
  'use strict';

  $(document).ready(function() {
    var $inline = $('.vehicle-photos-inline');
    if (!$inline.length) return;

    var vehicleId = (function() {
      var m = location.pathname.match(/\/vehicle\/(\d+)\//);
      return m ? m[1] : null;
    })();
    if (!vehicleId) return;

    var baseUrl = '/admin/rentals/vehicle/' + vehicleId + '/photos';

    function reloadTable() {
      $inline.find('tbody').load(
        window.location.pathname + ' .vehicle-photos-inline tbody > *',
        function() {
          bindEvents();
          updateEmptyState();
        }
      );
    }

    function updateEmptyState() {
      var $tbody = $inline.find('tbody');
      var rows = $tbody.find('tr.photo-row').length;
      var $msg = $tbody.find('.no-photos-msg');
      if (rows === 0 && !$msg.length) {
        $tbody.append('<tr><td colspan="3" class="no-photos-msg">Belum ada foto. Pilih gambar di atas lalu klik <strong>Upload Foto</strong>.</td></tr>');
      } else if (rows > 0 && $msg.length) {
        $msg.closest('tr').remove();
      }
    }

    function bindEvents() {
      $inline.find('.photo-delete-btn').off('click').on('click', function(e) {
        e.preventDefault();
        var $row = $(this).closest('tr');
        var photoId = $row.data('photo-id');
        if (!confirm('Yakin ingin menghapus foto ini?')) return;

        $.post(baseUrl + '/' + photoId + '/delete/', function(res) {
          if (res.ok) {
            $row.fadeOut(300, function() { $row.remove(); updateEmptyState(); });
          } else {
            alert(res.error || 'Gagal menghapus.');
          }
        }).fail(function() { alert('Gagal menghapus. Coba lagi.'); });
      });

      $inline.find('.photo-order-input').off('change').on('change', function() {
        var $row = $(this).closest('tr');
        var photoId = $row.data('photo-id');
        $.post(baseUrl + '/' + photoId + '/order/', { order: this.value }, function(res) {
          if (!res.ok) alert(res.error || 'Gagal update urutan.');
        }).fail(function() {});
      });

      $inline.find('.photo-thumb').off('click').on('click', function() {
        var src = $(this).attr('src');
        if (src) window.open(src, '_blank');
      });
    }

    // Upload
    var $input = $inline.find('.photo-upload-input');
    var $btn = $inline.find('.photo-upload-btn');
    var $preview = $inline.find('.photo-upload-preview');

    $input.on('change', function() {
      var count = this.files.length;
      if (count) {
        $preview.text(count + ' file dipilih').css('color', '#212529');
      } else {
        $preview.text('Belum ada file dipilih').css('color', '#6c757d');
      }
    });

    $btn.on('click', function() {
      var file = $input[0].files[0];
      if (!file) { alert('Pilih gambar terlebih dahulu.'); return; }
      if (file.size > 1048576) { alert('Ukuran gambar maksimal 1 MB.'); return; }

      $btn.prop('disabled', true).text('Mengupload...');

      var fd = new FormData();
      fd.append('image', file);

      $.ajax({
        url: baseUrl + '/upload/',
        type: 'POST',
        data: fd,
        processData: false,
        contentType: false,
        success: function(res) {
          if (res.ok) {
            $input.val('');
            $preview.text('Belum ada file dipilih').css('color', '#6c757d');
            reloadTable();
          } else {
            alert(res.error || 'Gagal upload.');
          }
        },
        error: function() {
          alert('Gagal upload. Coba lagi.');
        },
        complete: function() {
          $btn.prop('disabled', false).text('Upload Foto');
        }
      });
    });

    bindEvents();
    updateEmptyState();
  });
})(django.jQuery);
