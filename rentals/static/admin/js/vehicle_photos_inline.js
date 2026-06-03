(function() {
  'use strict';

  function init() {
    var inline = document.querySelector('.vehicle-photos-inline');
    if (!inline) return;

    var vehicleId = (function() {
      var m = location.pathname.match(/\/vehicle\/(\d+)\//);
      return m ? m[1] : null;
    })();
    if (!vehicleId) return;

    var baseUrl = '/admin/rentals/vehicle/' + vehicleId + '/photos';

    function csrfToken() {
      var name = 'csrftoken';
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.indexOf(name + '=') === 0) return c.substring(name.length + 1);
      }
      return '';
    }

    function apiPost(path, body) {
      return fetch(path, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken() },
        body: body
      }).then(function(r) { return r.json(); });
    }

    function apiPostForm(path, formData) {
      return fetch(path, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken() },
        body: formData
      }).then(function(r) { return r.json(); });
    }

    function reloadTable() {
      var tbody = inline.querySelector('tbody');
      if (!tbody) return;
      fetch(location.pathname + '?' + Date.now(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(r) { return r.text(); })
        .then(function(html) {
          var tmp = document.createElement('div');
          tmp.innerHTML = html;
          var newTbody = tmp.querySelector('.vehicle-photos-inline tbody');
          if (newTbody) {
            tbody.innerHTML = newTbody.innerHTML;
            bindEvents();
            updateEmptyState();
          }
        })
        .catch(function() { location.reload(); });
    }

    function updateEmptyState() {
      var tbody = inline.querySelector('tbody');
      if (!tbody) return;
      var rows = tbody.querySelectorAll('tr.photo-row');
      var msg = tbody.querySelector('.no-photos-msg');
      if (rows.length === 0 && !msg) {
        var tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="3" class="no-photos-msg">Belum ada foto. Pilih gambar di atas lalu klik <strong>Upload Foto</strong>.</td>';
        tbody.appendChild(tr);
      } else if (rows.length > 0 && msg) {
        msg.parentNode.remove();
      }
    }

    function bindEvents() {
      inline.querySelectorAll('.photo-delete-btn').forEach(function(btn) {
        btn.onclick = function(e) {
          e.preventDefault();
          var row = btn.closest('tr');
          var photoId = row.getAttribute('data-photo-id');
          if (!confirm('Yakin ingin menghapus foto ini?')) return;
          var fd = new FormData();
          apiPost(baseUrl + '/' + photoId + '/delete/', fd).then(function(res) {
            if (res.ok) {
              row.style.transition = 'opacity .3s';
              row.style.opacity = '0';
              setTimeout(function() { row.remove(); updateEmptyState(); }, 300);
            } else { alert(res.error || 'Gagal menghapus.'); }
          }).catch(function() { alert('Gagal menghapus.'); });
        };
      });

      inline.querySelectorAll('.photo-order-input').forEach(function(input) {
        input.onchange = function() {
          var row = input.closest('tr');
          var photoId = row.getAttribute('data-photo-id');
          var fd = new FormData();
          fd.append('order', input.value);
          apiPost(baseUrl + '/' + photoId + '/order/', fd).then(function(res) {
            if (!res.ok) alert(res.error || 'Gagal update.');
          }).catch(function() {});
        };
      });

      inline.querySelectorAll('.photo-thumb').forEach(function(img) {
        img.onclick = function() {
          if (img.src) window.open(img.src, '_blank');
        };
      });
    }

    var fileInput = inline.querySelector('.photo-upload-input');
    var uploadBtn = inline.querySelector('.photo-upload-btn');
    var previewName = inline.querySelector('.photo-upload-preview');

    if (fileInput) {
      fileInput.onchange = function() {
        if (fileInput.files.length) {
          previewName.textContent = fileInput.files.length + ' file dipilih';
          previewName.style.color = '#212529';
        } else {
          previewName.textContent = 'Belum ada file dipilih';
          previewName.style.color = '#6c757d';
        }
      };
    }

    if (uploadBtn) {
      uploadBtn.onclick = function() {
        var file = fileInput.files[0];
        if (!file) { alert('Pilih gambar terlebih dahulu.'); return; }
        if (file.size > 1048576) { alert('Ukuran gambar maksimal 1 MB.'); return; }

        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Mengupload...';

        var fd = new FormData();
        fd.append('image', file);

        apiPostForm(baseUrl + '/upload/', fd).then(function(res) {
          if (res.ok) {
            fileInput.value = '';
            previewName.textContent = 'Belum ada file dipilih';
            previewName.style.color = '#6c757d';
            reloadTable();
          } else { alert(res.error || 'Gagal upload.'); }
        }).catch(function() { alert('Gagal upload.'); })
          .finally(function() {
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Upload Foto';
          });
      };
    }

    bindEvents();
    updateEmptyState();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
