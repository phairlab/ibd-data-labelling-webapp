// IBD Patient Timeline Viewer — client-side rendering logic
// Data (ALL_EVENTS, FLARES) is injected by Python into window before this script runs.

var FIXED = [
    'imaging',
    'prescription',
    'physician_claim',
    'lab_test',
    'ambulatory_visit',
    'hospital_admission'
];

var LABELS = {
    'imaging':            'Diagnostic Imaging',
    'prescription':       'Prescription',
    'physician_claim':    'Physician Claim',
    'lab_test':           'Lab Test',
    'ambulatory_visit':   'Ambulatory Visit',
    'hospital_admission': 'Hospitalization'
};

var COLORS = {
    'imaging':            '#636EFA',
    'prescription':       '#EF553B',
    'physician_claim':    '#AB63FA',
    'lab_test':           '#19D3F3',
    'ambulatory_visit':   '#00CC96',
    'hospital_admission': '#FFA15A'
};

function filterEvents(filter) {
    if (filter === 'ibd')     return ALL_EVENTS.filter(function(e){ return  e.ibd_related; });
    if (filter === 'non_ibd') return ALL_EVENTS.filter(function(e){ return !e.ibd_related; });
    return ALL_EVENTS;
}

function buildHoverText(e) {
    var label = LABELS[e.event_type] || e.event_type || '';
    var t = (label ? '<b>event_type:</b> ' + label + '<br>' : '') +
            '<b>start:</b> ' + e.start_date.split('T')[0] +
            '<br><b>end:</b> ' + e.end_date.split('T')[0] + '<br>';
    try {
        var info = typeof e.event_info === 'string' ? JSON.parse(e.event_info) : e.event_info;
        Object.keys(info).forEach(function(k) {
            if (k === 'dummy') return;
            var v = String(info[k]);
            if (v.length > 40) {
                var chunks = [];
                for (var i = 0; i < v.length; i += 40) chunks.push(v.slice(i, i + 40));
                t += '<b>' + k + ':</b><br>' + chunks.join('<br>') + '<br>';
            } else {
                t += '<b>' + k + ':</b> ' + v + '<br>';
            }
        });
    } catch (err) {
        // Plain string event_info (e.g. "At: Hospital | Dx: ... | CMG: ...")
        var raw = e.event_info ? String(e.event_info).trim() : '';
        if (raw) {
            raw.split(' | ').forEach(function(part) {
                var ci = part.indexOf(': ');
                if (ci > 0) {
                    t += '<b>' + part.slice(0, ci) + ':</b> ' + part.slice(ci + 2) + '<br>';
                } else if (part) {
                    t += part + '<br>';
                }
            });
        }
    }
    if (e.source_dataset) t += '<b>source_dataset:</b> ' + e.source_dataset + '<br>';
    t += '<b>ibd_related:</b> ' + e.ibd_related;
    return t;
}

function processEvents(events) {
    var result = events.map(function(e) { return Object.assign({}, e); });

    result.forEach(function(e) {
        e._s = new Date(e.start_date).getTime();
        e._e = new Date(e.end_date).getTime();
        if (e._s === e._e) e._e += 86400000;
    });

    // Stagger same-day lab tests by 2 hours each so they don't overlap
    var labByDate = {};
    result.filter(function(e) { return e.event_type === 'lab_test'; })
          .forEach(function(e) {
              var k = e.start_date.split('T')[0];
              if (!labByDate[k]) labByDate[k] = [];
              labByDate[k].push(e);
          });
    Object.keys(labByDate).forEach(function(k) {
        var grp = labByDate[k];
        if (grp.length > 1) grp.forEach(function(e, i) {
            var offset = i * 7200000;
            e._s += offset;
            e._e += offset;
        });
    });

    return result;
}

// Move Plotly's modebar into the filter bar so it sits on the same row
function relocateModebar() {
    setTimeout(function() {
        var modebar   = document.querySelector('.js-plotly-plot .modebar-container');
        var filterBar = document.getElementById('filter-bar');
        if (modebar && filterBar && modebar.parentElement !== filterBar) {
            filterBar.appendChild(modebar);
        }
    }, 80);
}

var _chartReady = false;
var _relayoutBound = false;
var _clampingZoom = false;
var MAX_VIEW_WIDTH = null;
var DEFAULT_MIN = null, DEFAULT_MAX = null;
var _currentFilter = 'all';

// The chart lives inside an iframe (srcdoc, same-origin as the parent app),
// so it can read the parent's dark/light choice straight off <html data-theme>
// instead of needing its own separate toggle or a postMessage round trip.
function themeColors() {
    var dark = false;
    try { dark = window.parent.document.documentElement.getAttribute('data-theme') === 'dark'; } catch (e) {}
    return dark
        ? { bg: 'rgba(0,0,0,0)', font: '#dbe8e4', grid: 'rgba(219,232,228,.14)', line: 'rgba(219,232,228,.3)' }
        : { bg: '#ffffff', font: '#152826', grid: '#eef3f1', line: '#d7e1de' };
}

// Zooming in is unrestricted, but zooming OUT (clicking "-", scrolling out,
// drag-zoom, Autoscale, Reset axes) can't go past the default view the chart
// first loaded with — past that the bars are too compressed to read, so
// snap back to the default instead of letting the view keep widening.
function clampMaxZoom(eventData) {
    if (_clampingZoom || !eventData) return;

    if (MAX_VIEW_WIDTH === null) return;

    if (eventData['xaxis.autorange'] === true) {
        // Autoscale/Reset axes resets via Plotly's own fit-to-ALL-data
        // autorange, which includes any stray outlier dates (e.g. a 1970
        // record) — centering a normal-width window on THAT range's
        // midpoint can land in decades of empty space with no bars in
        // sight at all, even though the DOM still has them. The default
        // view (tMin/tMax below) was already computed to exclude such
        // outliers via percentiles, so just snap straight back to it —
        // that's the one range guaranteed to actually show the data.
        _clampingZoom = true;
        Plotly.relayout('plot', {
            'xaxis.range[0]': DEFAULT_MIN,
            'xaxis.range[1]': DEFAULT_MAX
        }).then(function() { _clampingZoom = false; });
        return;
    }

    var hasMin = Object.prototype.hasOwnProperty.call(eventData, 'xaxis.range[0]');
    var hasMax = Object.prototype.hasOwnProperty.call(eventData, 'xaxis.range[1]');
    if (!hasMin || !hasMax) return;
    var r0 = new Date(eventData['xaxis.range[0]']).getTime();
    var r1 = new Date(eventData['xaxis.range[1]']).getTime();

    var width = r1 - r0;
    if (width > MAX_VIEW_WIDTH) {
        var center = (r0 + r1) / 2;
        _clampingZoom = true;
        Plotly.relayout('plot', {
            'xaxis.range[0]': center - MAX_VIEW_WIDTH / 2,
            'xaxis.range[1]': center + MAX_VIEW_WIDTH / 2
        }).then(function() { _clampingZoom = false; });
    }
}

// Row spacing between the 6 fixed category rows — "+"/"-" on the modebar
// adjust how much of each row's slot the bar fills (BASE = tight/default,
// MIN = most spread out). Never exceeds BASE in either direction, so there's
// no unfilled/blank space: the bar always occupies some fraction of its own
// fixed-height row slot, nothing more.
var ROW_SPACING_LEVEL = 0;
var ROW_SPACING_MAX_LEVEL = 5;
var ROW_SPACING_BASE_WIDTH = 0.9;
var ROW_SPACING_MIN_WIDTH = 0.3;

function currentRowBarWidth() {
    var step = (ROW_SPACING_BASE_WIDTH - ROW_SPACING_MIN_WIDTH) / ROW_SPACING_MAX_LEVEL;
    return ROW_SPACING_BASE_WIDTH - ROW_SPACING_LEVEL * step;
}

function adjustRowSpacing(direction) {
    if (direction > 0) {
        ROW_SPACING_LEVEL = Math.min(ROW_SPACING_MAX_LEVEL, ROW_SPACING_LEVEL + 1);
    } else {
        ROW_SPACING_LEVEL = Math.max(0, ROW_SPACING_LEVEL - 1);
    }
    Plotly.restyle('plot', { width: currentRowBarWidth() });
}

function renderChart(filter) {
    var events = processEvents(filterEvents(filter));
    var ref    = ALL_EVENTS.length ? new Date(ALL_EVENTS[0].start_date).getTime() : Date.now();
    var barWidth = currentRowBarWidth();

    var traces = FIXED.map(function(et) {
        var te    = events.filter(function(e) { return e.event_type === et; });
        var dummy = te.length === 0;
        return {
            type:          'bar',
            orientation:   'h',
            name:          LABELS[et] || et,
            x:             dummy ? [0]   : te.map(function(e) { return e._e - e._s; }),
            base:          dummy ? [ref] : te.map(function(e) { return e._s; }),
            y:             dummy ? [et]  : te.map(function()  { return et; }),
            customdata:    dummy ? ['']  : te.map(function(e) { return buildHoverText(e); }),
            hovertemplate: dummy ? '<extra></extra>' : '%{customdata}<extra></extra>',
            textposition:  'none',
            marker:        { color: COLORS[et] || '#888', opacity: dummy ? 0 : 1 },
            width:         dummy ? 0 : barWidth,
            showlegend:    false
        };
    });

    var shapes = FLARES.map(function(f) {
        return {
            type: 'rect', xref: 'x', yref: 'paper',
            x0: f.start_date, x1: f.end_date,
            y0: 0, y1: 1,
            fillcolor: 'red', opacity: 0.3,
            layer: 'below', line: { width: 0 }
        };
    });

    var sMs  = ALL_EVENTS.map(function(e) { return new Date(e.start_date).getTime(); });
    var eMs  = ALL_EVENTS.map(function(e) { return new Date(e.end_date).getTime(); });

    // Default view should focus on where the real data lives — a single stray
    // outlier date (e.g. a 1970 record) shouldn't stretch the whole axis and
    // squeeze everything else into a sliver. Use the 2nd/98th percentile for
    // the initial range. This also becomes the zoom-out ceiling below.
    function percentileMs(arr, p) {
        var s = arr.slice().sort(function(a, b) { return a - b; });
        var idx = (s.length - 1) * p;
        var lo = Math.floor(idx), hi = Math.ceil(idx);
        return lo === hi ? s[lo] : s[lo] + (s[hi] - s[lo]) * (idx - lo);
    }
    var allMs = sMs.concat(eMs);
    var tMin = allMs.length ? percentileMs(allMs, 0.02) - 864000000 : ref - 864000000;
    var tMax = allMs.length ? percentileMs(allMs, 0.98) + 864000000 : ref + 864000000;

    // Zooming out can't go past the default view width — beyond this the
    // bars are too compressed to read. Zooming in stays unrestricted.
    MAX_VIEW_WIDTH = tMax - tMin;
    DEFAULT_MIN = tMin;
    DEFAULT_MAX = tMax;

    var theme = themeColors();
    var layout = {
        xaxis: { type: 'date', title: 'Time', range: [tMin, tMax],
                 gridcolor: theme.grid, linecolor: theme.line, zerolinecolor: theme.line,
                 tickfont: { color: theme.font }, titlefont: { color: theme.font } },
        yaxis: {
            title:         'Event Type',
            categoryorder: 'array',
            categoryarray: FIXED,
            tickvals:      FIXED,
            ticktext:      FIXED.map(function(et) { return LABELS[et] || et; }),
            gridcolor: theme.grid, linecolor: theme.line, zerolinecolor: theme.line,
            tickfont: { color: theme.font }, titlefont: { color: theme.font }
        },
        barmode:       'overlay',
        showlegend:    false,
        autosize:      true,
        margin:        { l: 120, r: 20, t: 16, b: 40 },
        shapes:        shapes,
        hovermode:     'closest',
        bargap:        0.1,
        bargroupgap:   0.0,
        font:          { color: theme.font },
        plot_bgcolor:  theme.bg,
        paper_bgcolor: theme.bg
    };

    var config = {
        responsive:             true,
        displayModeBar:         true,
        // Built-in zoomIn2d/zoomOut2d zoom the TIME (x) axis — replaced with
        // custom +/- buttons that instead adjust vertical spacing between
        // the 6 category rows. Drag-to-zoom and scroll-zoom still control
        // time, unaffected.
        modeBarButtonsToRemove: ['select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d'],
        modeBarButtonsToAdd: [
            {
                name: 'Increase row spacing',
                icon: Plotly.Icons.zoom_plus,
                click: function() { adjustRowSpacing(-1); }
            },
            {
                name: 'Decrease row spacing',
                icon: Plotly.Icons.zoom_minus,
                click: function() { adjustRowSpacing(1); }
            }
        ]
    };

    if (!_chartReady) {
        Plotly.newPlot('plot', traces, layout, config);
        _chartReady = true;
        relocateModebar();
    } else {
        Plotly.react('plot', traces, layout, config);
    }

    if (!_relayoutBound) {
        document.getElementById('plot').on('plotly_relayout', clampMaxZoom);
        _relayoutBound = true;
    }
}

// Filter button handler — called by onclick in the HTML
window.setF = function(filter) {
    document.querySelectorAll('.fbtn').forEach(function(b) { b.className = 'fbtn off'; });
    var idx = { all: 0, ibd: 1, non_ibd: 2 };
    document.querySelectorAll('.fbtn')[idx[filter]].className = 'fbtn on';
    _currentFilter = filter;
    renderChart(filter);
};

// Called by the parent page right after it flips light/dark, so the chart's
// own colours (which Plotly bakes into the SVG rather than styling via CSS)
// re-render to match instead of staying stuck in the old theme.
window.ptvApplyTheme = function() {
    if (_chartReady) renderChart(_currentFilter);
};

// Load Plotly from the CDN script already in <head> — NEVER borrow
// window.parent.Plotly. Once Labelling Mode's gr.Plot() component has run,
// window.parent.Plotly exists but is internally bound to the PARENT page's
// document, not this iframe's — using it makes Plotly.newPlot('plot', ...)
// fail with "No DOM element with id 'plot' exists on the page" even though
// #plot is right here, because Plotly's own internals resolve against the
// wrong document. Every render must use a Plotly instance loaded inside
// THIS document.
function initPlotly() {
    if (typeof Plotly !== 'undefined') {
        renderChart('all');
        return;
    }

    // CDN in <head> may still be loading — poll for up to 10 s
    var attempts = 0;
    var iv = setInterval(function() {
        if (typeof Plotly !== 'undefined') {
            clearInterval(iv);
            renderChart('all');
        } else if (++attempts > 100) {
            clearInterval(iv);
            document.getElementById('plot').innerHTML =
                '<p style="color:#ef4444;padding:20px;">Could not load chart library ' +
                '(no internet access). Contact your administrator.</p>';
        }
    }, 100);
}

initPlotly();
