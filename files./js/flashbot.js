/**
 * FlashBot — shared JavaScript
 * Handles: CRT overlays, scroll-reveal, tab switching,
 *          hero terminal, board-status demo, interactive pipeline terminal,
 *          guide progress tracker, API search & filter.
 */

(function () {
  'use strict';

  /* ─────────────────────────────────────────────
     1. CRT / visual overlays
  ───────────────────────────────────────────── */
  function initOverlays() {
    // Phosphor-dot overlay
    var op = document.createElement('div');
    op.className = 'op';
    document.body.appendChild(op);

    // Skeleton fade-out on load
    var skel = document.createElement('div');
    skel.className = 'skel-o ld';
    document.body.appendChild(skel);
    setTimeout(function () { skel.classList.remove('ld'); }, 550);
  }

  /* ─────────────────────────────────────────────
     2. Scroll-reveal
  ───────────────────────────────────────────── */
  function initScrollReveal() {
    var ro = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('rd'); }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -60px 0px' });

    document.querySelectorAll('.rev').forEach(function (el) { ro.observe(el); });
  }

  /* ─────────────────────────────────────────────
     3. Tab switching
  ───────────────────────────────────────────── */
  function revealVisible(pageId) {
    // Trigger reveal for elements already in viewport after tab switch
    setTimeout(function () {
      document.querySelectorAll('#' + pageId + ' .rev').forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) {
          el.classList.add('rd');
        }
      });
    }, 100);
  }

  window.switchTab = function (name, btn) {
    document.querySelectorAll('.tab-page').forEach(function (p) { p.classList.remove('active'); });
    document.querySelectorAll('.tab-link').forEach(function (l) { l.classList.remove('active'); });

    var page = document.getElementById('page-' + name);
    if (page) page.classList.add('active');
    if (btn)  btn.classList.add('active');

    document.body.scrollTop = document.documentElement.scrollTop = 0;
    revealVisible('page-' + name);
  };

  /* ─────────────────────────────────────────────
     4. Hero terminal — animated output lines
  ───────────────────────────────────────────── */
  var heroOutput = [
    { t: '╭────────────────── Board Detected ──────────────────╮', c: 'cyan' },
    { t: '│ Arduino Uno WiFi R4                                │', c: '' },
    { t: '│ Port:  /dev/ttyACM0                                │', c: '' },
    { t: '│ FQBN:  arduino:renesas_uno:unor4wifi               │', c: '' },
    { t: '╰────────────────────────────────────────────────────╯', c: 'cyan' },
    { t: 'Auto-selected: sketches/arduino/renesas_uno/unor4wifi/blink/blink.ino', c: 'dim' },
    { t: 'Sketch unchanged — skipping compile.', c: 'dim' },
    { t: 'FLASH OK                    All Tests Passed', c: 'ok' },
  ];

  function initHeroTerminal() {
    var delay = 0;
    heroOutput.forEach(function (ln, i) {
      var el = document.getElementById('hl' + i);
      if (!el) return;
      setTimeout(function () {
        el.textContent = ln.t;
        el.className = 'l ' + ln.c;
      }, delay);
      delay += 120;
    });
  }

  /* ─────────────────────────────────────────────
     5. Board-status demo (click to cycle)
  ───────────────────────────────────────────── */
  var boardPhases = [
    { d: 'idle',  l: 'no board detected',             s: '' },
    { d: 'scan',  l: 'listening for USB hotplug...',  s: '' },
    { d: 'scan',  l: 'device connected on /dev/ttyACM0', s: '' },
    { d: 'conn',  l: 'Arduino Uno WiFi R4 detected',  s: 'arduino:renesas_uno:unor4wifi' },
    { d: 'flash', l: 'compiling blink.ino...',         s: 'SHA-256 skip' },
    { d: 'flash', l: 'uploading firmware',             s: '115200 baud' },
    { d: 'done',  l: 'flash OK — all tests passed',   s: '5.2s' },
    { d: 'idle',  l: 'waiting for next board...',     s: '' },
  ];

  function initBoardStatus() {
    var sd = document.getElementById('statusDot');
    var sl = document.getElementById('statusLabel');
    var st = document.getElementById('statusTime');
    var be = document.getElementById('boardStatus');
    if (!be) return;

    var timer = null;
    var phase = 0;

    function cycle() {
      if (timer) return;
      phase = 0;
      timer = setInterval(function () {
        var p = boardPhases[phase % boardPhases.length];
        if (sd) sd.className = 'sd ' + p.d;
        if (sl) sl.textContent = p.l;
        if (st) st.textContent = p.s;
        phase++;
        if (phase >= boardPhases.length) { clearInterval(timer); timer = null; }
      }, 900);
    }

    be.addEventListener('click', function () {
      if (timer) { clearInterval(timer); timer = null; }
      cycle();
    });
  }

  /* ─────────────────────────────────────────────
     6. Interactive pipeline terminal
  ───────────────────────────────────────────── */
  var pipelineOutputs = {
    flash: [
      { t: '╭────────────────── Board Detected ──────────────────╮', c: 'cyan' },
      { t: '│ Arduino Uno WiFi R4                                │', c: '' },
      { t: '│ Port:  /dev/ttyACM0                                │', c: '' },
      { t: '╰────────────────────────────────────────────────────╯', c: 'cyan' },
      { t: 'Auto-selected: sketches/arduino/renesas_uno/unor4wifi/blink/blink.ino', c: 'dim' },
      { t: 'Sketch unchanged — skipping compile.', c: 'dim' },
      { t: 'FLASH OK                    All Tests Passed', c: 'ok' },
    ],
    report: [
      { t: 'Flash History', c: 'cyan' },
      { t: 'ID  Board         FQBN                          Sketch          Status  Timestamp', c: '' },
      { t: '──  ─────         ────                          ──────          ──────  ─────────', c: 'dim' },
      { t: ' 3  Uno WiFi R4   arduino:renesas_uno:unor4wifi  blink          SUCCESS  2026-05-28', c: '' },
      { t: ' 2  Uno WiFi R4   arduino:renesas_uno:unor4wifi  serial_test    SUCCESS  2026-05-27', c: '' },
      { t: ' 1  Uno WiFi R4   arduino:renesas_uno:unor4wifi  blink          FAILED   2026-05-26', c: '' },
      { t: '', c: '' },
    ],
    unknown: [
      { t: '╭────────────────── Unknown Board ───────────────────╮', c: 'warn' },
      { t: '│ Port:   /dev/ttyUSB0                               │', c: '' },
      { t: '│ VID:    10c4                                       │', c: '' },
      { t: '│ PID:    ea60                                       │', c: '' },
      { t: '╰────────────────────────────────────────────────────╯', c: 'warn' },
      { t: 'Enter board name [My Board]: ESP32 DevKit', c: '' },
      { t: 'Registered ESP32 DevKit — FQBN: esp32:esp32:esp32', c: 'ok' },
    ],
    watch: [
      { t: 'Watching for MCU connections...', c: '' },
      { t: '[14:32:01] + Board: Arduino Uno WiFi R4', c: 'ok' },
      { t: '[14:32:01]   → auto-selected: blink', c: '' },
      { t: '[14:32:01]   → compiling...', c: '' },
      { t: '[14:32:07]   ✓ flash OK', c: 'ok' },
      { t: '[14:32:09]   ✓ all tests passed', c: 'ok' },
      { t: '[14:32:10] - board disconnected', c: 'dim' },
    ],
  };

  var cmdLabels = {
    flash:   'python flashbot.py',
    report:  'python flashbot.py report',
    unknown: 'python flashbot.py',
    watch:   'python flashbot.py',
  };

  window.runPipeline = function (cmd) {
    var lines = pipelineOutputs[cmd] || pipelineOutputs.flash;
    var cmdEl = document.getElementById('termCmd');
    if (cmdEl) cmdEl.textContent = cmdLabels[cmd] || 'python flashbot.py';

    // Highlight active button
    var btnMap = { flash: 0, report: 1, unknown: 2, watch: 3 };
    document.querySelectorAll('.term-actions button').forEach(function (b, i) {
      b.classList.toggle('act', i === btnMap[cmd]);
    });

    // Animate lines
    var delay = 0;
    for (var i = 0; i < 7; i++) {
      (function (idx) {
        var el = document.getElementById('termL' + idx);
        if (!el) return;
        var ln = lines[idx] || { t: '', c: 'dim' };
        setTimeout(function () {
          el.textContent = ln.t;
          el.className = 'l ' + ln.c;
        }, delay);
        delay += 100;
      })(i);
    }
  };

  /* ─────────────────────────────────────────────
     7. Guide — progress tracker
  ───────────────────────────────────────────── */
  window.jumpTo = function (n) {
    document.querySelectorAll('.prog-track .pt').forEach(function (t, i) {
      t.classList.toggle('act',  i + 1 === n);
      t.classList.toggle('done', i + 1 <  n);
    });
    var target = document.getElementById('s' + n);
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  window.toggleExp = function (hd) {
    hd.classList.toggle('open');
    var bd = hd.nextElementSibling;
    if (bd) bd.classList.toggle('open');
  };

  function initGuideObserver() {
    var pts = document.querySelectorAll('.prog-track .pt');
    if (!pts.length) return;

    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var n = parseInt(e.target.id.replace('s', ''), 10);
        if (isNaN(n)) return;
        pts.forEach(function (t, i) {
          t.classList.toggle('act',  i + 1 === n);
          t.classList.toggle('done', i + 1 <  n);
        });
      });
    }, { threshold: 0.3 });

    document.querySelectorAll('.doc-sec[id^="s"]').forEach(function (el) { obs.observe(el); });
  }

  /* ─────────────────────────────────────────────
     8. API page — search & filter
  ───────────────────────────────────────────── */
  window.filterAll = function (q) {
    q = (q || '').toLowerCase().trim();
    var clr = document.getElementById('clrBtn');
    if (clr) clr.classList.toggle('vis', q.length > 0);

    document.querySelectorAll('#cmdTbl tbody tr').forEach(function (r) {
      r.style.display = (!q || r.textContent.toLowerCase().includes(q)) ? '' : 'none';
    });
    document.querySelectorAll('#page-api .doc-sec').forEach(function (s) {
      if (!q) { s.style.display = ''; return; }
      s.style.display = s.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  };

  window.clrSearch = function () {
    var inp = document.getElementById('searchIn');
    if (inp) { inp.value = ''; window.filterAll(''); }
  };

  window.fltCmds = function (tag, btn) {
    document.querySelectorAll('.flt-tabs button').forEach(function (b) { b.classList.remove('act'); });
    btn.classList.add('act');
    document.querySelectorAll('#cmdTbl tbody tr').forEach(function (r) {
      r.style.display = (tag === 'all' || r.getAttribute('data-tag') === tag) ? '' : 'none';
    });
  };

  /* ─────────────────────────────────────────────
     Boot
  ───────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    initOverlays();
    initScrollReveal();
    initHeroTerminal();
    initBoardStatus();
    initGuideObserver();

    // Only auto-run pipeline on home tab (element exists)
    if (document.getElementById('termL0')) {
      window.runPipeline('flash');
    }
  });

})();
