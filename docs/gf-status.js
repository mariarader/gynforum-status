(function () {
  var STATUS_URL =
    'https://raw.githubusercontent.com/mariarader/gynforum-status/main/data/status.json';

  var ICONS = {
    Plaster: '🩹', Gel: '🧴', Spray: '💨', Tablett: '💊',
    Vaginaltablett: '🌸', 'Vagitorier/krem': '🌸', Vaginalgel: '🌸'
  };

  function bdg(t, s) {
    return '<span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;border:1px solid;white-space:nowrap;' + s + '">' + t + '</span>';
  }
  function dot(c) {
    return '<span style="width:7px;height:7px;border-radius:50%;background:' + c + ';display:inline-block;flex-shrink:0;"></span>';
  }
  function pill(p) {
    if (p.has_shortage === true)
      return bdg(dot('#902828') + ' Mangel meldt', 'background:#FDF0F0;color:#902828;border-color:#E0B0B0;');
    if (p.has_shortage === false)
      return bdg(dot('#2E7050') + ' Ingen mangel', 'background:#EEF7F2;color:#2E7050;border-color:#A8D4BC;');
    return bdg('Ukjent', 'background:#F5F5F5;color:#888;border-color:#DDD;');
  }
  function alink(n, u) {
    return '<a href="' + u + '" target="_blank" rel="noopener" style="font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;border:1.5px solid #E2D9E8;color:#5C3D5E;text-decoration:none;white-space:nowrap;background:white;display:inline-block;">' + n + '</a>';
  }
  function buildTable(preps) {
    var thBase = 'padding:9px 12px;text-align:left;color:white;font-size:11px;letter-spacing:0.04em;text-transform:uppercase;font-weight:500;';
    var rows = preps.map(function (p) {
      var ic = ICONS[p.form] || '💊';
      var pk = p.packages.map(function (x) { return x.label; }).join(' · ');
      var det = '';
      if (p.has_shortage) {
        if (p.shortage_period) det += '<div style="font-size:11px;color:#902828;margin-top:3px;">Periode: ' + p.shortage_period + '</div>';
        if (p.shortage_reason) det += '<div style="font-size:11px;color:#902828;">Årsak: ' + p.shortage_reason + '</div>';
      }
      var al = Object.entries(p.apotek_links).map(function (e) { return alink(e[0], e[1]); }).join(' ');
      var td = 'padding:10px 12px;border-bottom:1px solid #E2D9E8;vertical-align:middle;';
      return '<tr>' +
        '<td style="' + td + '"><strong>' + ic + ' ' + p.name + '</strong><br><span style="font-size:11px;color:#7A7480;">' + pk + '</span></td>' +
        '<td style="' + td + 'font-size:12px;color:#7A7480;">' + p.form + '</td>' +
        '<td style="' + td + '">' + pill(p) + det + '</td>' +
        '<td style="' + td + '"><div style="display:flex;flex-wrap:wrap;gap:4px;">' + al + '</div></td>' +
        '<td style="' + td + '"><a href="' + p.dmp_search_url + '" target="_blank" style="font-size:11px;color:#5C3D5E;text-decoration:none;">DMP ↗</a></td>' +
        '</tr>';
    }).join('');
    return '<div style="overflow-x:auto;border:1px solid #E2D9E8;border-radius:10px;margin-bottom:8px;">' +
      '<table style="width:100%;border-collapse:collapse;font-size:13px;">' +
      '<thead><tr style="background:#5C3D5E;">' +
      '<th style="' + thBase + 'border-radius:9px 0 0 0;">Preparat</th>' +
      '<th style="' + thBase + '">Form</th>' +
      '<th style="' + thBase + '">DMP-status</th>' +
      '<th style="' + thBase + '">Sjekk apotek</th>' +
      '<th style="' + thBase + 'border-radius:0 9px 0 0;">DMP</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  function render(data) {
    var s = data.summary;
    var ub = document.getElementById('gf-updated');
    if (ub) ub.innerHTML = 'Sist oppdatert: <strong>' + data.generated_display + '</strong>';
    var bb = document.getElementById('gf-badges');
    if (bb) {
      bb.innerHTML =
        bdg(dot('#2E7050') + ' ' + s.ok + ' uten mangel', 'background:#EEF7F2;color:#2E7050;border-color:#A8D4BC;') +
        (s.with_shortage > 0 ? ' ' + bdg(dot('#902828') + ' ' + s.with_shortage + ' med mangel', 'background:#FDF0F0;color:#902828;border-color:#E0B0B0;') : '');
    }
    var sys = data.preparations.filter(function (p) { return p.type === 'systemisk'; });
    var vag = data.preparations.filter(function (p) { return p.type === 'vaginal'; });
    var h = '';
    if (sys.length) h += '<h3 style="font-family:serif;font-style:italic;color:#5C3D5E;font-size:15px;margin:8px 0 8px;">Systemiske preparater</h3>' + buildTable(sys);
    if (vag.length) h += '<h3 style="font-family:serif;font-style:italic;color:#5C3D5E;font-size:15px;margin:20px 0 8px;">Vaginale preparater</h3>' + buildTable(vag);
    var el = document.getElementById('gf-content');
    if (el) el.innerHTML = h;
  }

  function load() {
    fetch(STATUS_URL)
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () {
        var el = document.getElementById('gf-content');
        if (el) el.innerHTML = '<p style="color:#902828;font-size:13px;padding:1rem 0;">Kunne ikke laste statusdata. <a href="https://www.dmp.no/forsyningssikkerhet/legemiddelmangel" style="color:#5C3D5E;">Gå direkte til DMP →</a></p>';
      });
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
