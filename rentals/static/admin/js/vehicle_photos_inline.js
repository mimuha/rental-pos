(function() {
  'use strict';

  var inline = document.querySelector('.vehicle-photos-inline');
  if (!inline) return;

  var vehicleId = (function() {
    var m = location.pathname.match(/\/vehicle\/(\d+)\//);
    return m ? m[1] : null;
  })();
  if (!vehicleId) return;

  function csrfToken() {
    var name = 'csrftoken';
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var c = cookies[i].trim();
      if (c.indexOf(name + '=') === 0) {
        return c.substring(name.length + 1);
      }
    }
    return '';
  }

  function api(path, body, method) {
    method = method || 'POST';
    var opts = {
      method: method,
      headers: { 'X-CSRFToken': csrfToken() },
    };
    if (body instanceof FormData) {
      opts.body = body;
    } else if (body) {
      opts.body = body;
      opts.headers['Content-Type'] = 'application/x-www-form-urlencoded';
    }
    return fetch(path, opts).then(function(r) { return r.json(); });
  }

  function reloadTable() {
    var tbody = inline.querySelector('tbody');
    if (!tbody) return;
    fetch('/admin/rentals/vehicle/' + vehicleId + '/change/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function(r) { return r.text(); })
      .then(function(html) {
        var parser = new DOMParser();
        var doc = parser.parseFromString(html, 'text/html');
        var newTbody = doc.querySelector('.vehicle-photos-inline tbody');
        if (newTbody) {
          tbody.innerHTML = newTbody.innerHTML;
          bindEvents();
          updateEmptyState();
        }
      })
      .catch(function() {
        setTimeout(function() { location.reload(); }, 300);
      });
  }

  function updateEmptyState() {
    var tbody = inline.querySelector('tbody');
    var rows = tbody.querySelectorAll('tr.photo-row');
    var msg = tbody.querySelector('.no-photos-msg');
    if (rows.length === 0) {
      if (!msg) {
        var tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="3" class="no-photos-msg">Belum ada foto. Pilih gambar di atas lalu klik <strong>Upload</strong>.</td>';
        tbody.appendChild(tr);
      }
    } else {
      if (msg) msg.remove();
    }
  }

  function bindEvents() {
    // Delete
    inline.querySelectorAll('.photo-delete-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var row = btn.closest('tr');
        var photoId = row.getAttribute('data-photo-id');
        if (!confirm('Yakin ingin menghapus foto ini?')) return;
        api('/admin/rentals/vehicle/' + vehicleId + '/photos/' + photoId + '/delete/')
          .then(function(res) {
            if (res.ok) {
              row.style.opacity = '0';
              row.style.transition = 'opacity .3s';
              setTimeout(function() { row.remove(); updateEmptyState(); }, 300);
            } else {
              alert(res.error || 'Gagal menghapus.');
            }
          });
      });
    });

    // Order change
    inline.querySelectorAll('.photo-order-input').forEach(function(input) {
      input.addEventListener('change', function() {
        var row = input.closest('tr');
        var photoId = row.getAttribute('data-photo-id');
        var val = input.value;
        api('/admin/rentals/vehicle/' + vehicleId + '/photos/' + photoId + '/order/',
            'order=' + encodeURIComponent(val))
          .then(function(res) {
            if (!res.ok) alert(res.error || 'Gagal update urutan.');
          });
      });
    });

    // Thumbnail click → new tab
    inline.querySelectorAll('.photo-thumb').forEach(function(img) {
      img.addEventListener('click', function() {
        if (img.src) window.open(img.src, '_blank');
      });
    });
  }

  // --- Upload area ---
  var fileInput = inline.querySelector('.photo-upload-input');
  var uploadBtn = inline.querySelector('.photo-upload-btn');
  var previewName = inline.querySelector('.photo-upload-preview');

  if (fileInput) {
    fileInput.addEventListener('change', function() {
      if (fileInput.files.length) {
        previewName.textContent = fileInput.files.length + ' file dipilih';
        previewName.style.color = '#212529';
      } else {
        previewName.textContent = 'Belum ada file dipilih';
        previewName.style.color = '#6c757d';
      }
    });
  }

  if (uploadBtn) {
    uploadBtn.addEventListener('click', function() {
      var file = fileInput.files[0];
      if (!file) {
        alert('Pilih gambar terlebih dahulu.');
        return;
      }
      if (file.size > 1048576) {
        alert('Ukuran gambar maksimal 1 MB.');
        return;
      }

      uploadBtn.disabled = true;
      uploadBtn.textContent = 'Mengupload...';

      var formData = new FormData();
      formData.append('image', file);

      api('/admin/rentals/vehicle/' + vehicleId + '/photos/upload/', formData)
        .then(function(res) {
          if (res.ok) {
            fileInput.value = '';
            previewName.textContent = 'Belum ada file dipilih';
            previewName.style.color = '#6c757d';
            reloadTable();
          } else {
            alert(res.error || 'Gagal upload.');
          }
        })
        .catch(function() {
          alert('Gagal upload. Coba lagi.');
        })
        .finally(function() {
          uploadBtn.disabled = false;
          uploadBtn.textContent = 'Upload Foto';
        });
    });
  }

  bindEvents();
  updateEmptyState();
})();
