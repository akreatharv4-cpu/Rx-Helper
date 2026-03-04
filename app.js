// app.js
async function analyze() {
  let text = $('#text').val().trim();
  if (!text) {
    // Show alert if input is empty
    $('#result').html('<div class="alert alert-warning">Please enter prescription details.</div>');
    return;
  }

  // Disable button and show spinner
  const $btn = $('#analyzeBtn');
  const originalBtn = $btn.html();
  $btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Analyzing...');

  try {
    let res = await fetch("http://127.0.0.1:5000/analyze", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text})
    });
    let data = await res.json();

    // Build HTML output
    let html = '';
    if (data.data) {
      html += `<h4>Patient Information</h4>`;
      html += `<p><strong>Age:</strong> ${data.data.age || 'N/A'}</p>`;
      if (data.data.drugs.length > 0) {
        html += `<p><strong>Medications:</strong></p><ul>`;
        data.data.drugs.forEach(drug => {
          html += `<li>${drug}</li>`;
        });
        html += `</ul>`;
      }
    }
    // Alerts (e.g., missing age)
    if (data.alerts.length > 0) {
      data.alerts.forEach(alert => {
        html += `<div class="alert alert-warning">${alert}</div>`;
      });
    }
    // Drug interactions
    if (data.interactions.length > 0) {
      data.interactions.forEach(inter => {
        html += `<div class="alert alert-danger"><strong>Interaction:</strong> ${inter.msg} (Severity: ${inter.severity})</div>`;
      });
    }
    // Counseling advice
    if (data.counseling) {
      html += `<p><strong>Counseling Advice:</strong> ${data.counseling}</p>`;
    }

    $('#result').html(html);

  } catch (error) {
    $('#result').html('<div class="alert alert-danger">Error analyzing prescription. Please try again.</div>');
    console.error(error);
  } finally {
    // Re-enable button
    $btn.prop('disabled', false).html(originalBtn);
  }
}

// Bind click event after document is ready
$(document).ready(function() {
  $('#analyzeBtn').on('click', analyze);
});
import React, { useState } from 'react'
import { uploadFile, analyzeText } from '../api.js'

export default function UploadCard({ onResult, onError }) {
  const [file, setFile] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)

  async function doUpload() {
    if (!file) return
    setBusy(true)
    try {
      const r = await uploadFile(file)
      onResult?.(r)
    } catch (e) {
      onError?.(e)
    } finally {
      setBusy(false)
    }
  }

  async function doAnalyzeText() {
    if (!text.trim()) return
    setBusy(true)
    try {
      const r = await analyzeText(text, 'manual-input.txt')
      onResult?.(r)
    } catch (e) {
      onError?.(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h2>Upload / Input</h2>

      <label>Upload image or PDF</label>
      <input type="file" accept="image/*,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <div className="row" style={{ marginTop: 8 }}>
        <button className="primary" disabled={!file || busy} onClick={doUpload}>
          {busy ? 'Working…' : 'Upload & Analyze'}
        </button>
      </div>

      <hr style={{ border:0, borderTop:'1px solid #eee', margin:'14px 0' }} />

      <label>Or paste text</label>
      <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste OCR text here..." />
      <div className="row" style={{ marginTop: 8 }}>
        <button className="primary" disabled={!text.trim() || busy} onClick={doAnalyzeText}>
          {busy ? 'Working…' : 'Analyze Text'}
        </button>
        <button disabled={busy} onClick={() => setText('')}>Clear</button>
      </div>

      <p className="muted" style={{ marginTop: 10 }}>
        Tip: Handwritten OCR is hard. Use a sharp photo with good lighting and minimal tilt.
      </p>
    </div>
  )
}
import React from 'react'

export default function ResultView({ result }) {
  if (!result) return (
    <div>
      <h2>Result</h2>
      <div className="muted">Select a prescription from history or upload a new one.</div>
    </div>
  )

  const meds = result.extracted?.medications || []
  const patient = result.extracted?.patient || {}
  const flags = result.flags || []

  return (
    <div>
      <h2>Result — #{result.id}</h2>

      <div className="kv">
        <div className="muted">Source</div>
        <div>{result.source_type} {result.source_filename ? `— ${result.source_filename}` : ""}</div>

        <div className="muted">Created</div>
        <div>{result.created_at}</div>

        <div className="muted">Patient</div>
        <div>
          {patient.name || <span className="muted">(name missing)</span>} — Age: {patient.age || "?"} — Sex: {patient.sex || "?"}
        </div>
      </div>

      <h3 style={{ margin: '10px 0 6px' }}>Flags</h3>
      {flags.length === 0 && <div className="muted">No flags (from MVP rules).</div>}
      {flags.map((f, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <span className={"badge " + (f.severity || "moderate")}>{f.severity || "moderate"}</span>
          <b>{f.type}</b>
          <pre>{JSON.stringify(f.details, null, 2)}</pre>
        </div>
      ))}

      <h3 style={{ margin: '10px 0 6px' }}>Medications ({meds.length})</h3>
      {meds.length === 0 ? <div className="muted">No medication lines detected.</div> : (
        <pre>{JSON.stringify(meds, null, 2)}</pre>
      )}

      <h3 style={{ margin: '10px 0 6px' }}>Raw OCR Text</h3>
      <pre>{result.raw_text}</pre>
    </div>
  )
}
import React, { useEffect, useRef, useState } from 'react'
import { whoMetrics } from '../api.js'
import Chart from 'chart.js/auto'

export default function Dashboard() {
  const [m, setM] = useState(null)
  const [err, setErr] = useState(null)
  const canvasRef = useRef(null)
  const chartRef = useRef(null)

  async function load() {
    try {
      const data = await whoMetrics()
      setM(data)
      setErr(null)
    } catch (e) {
      setErr(String(e))
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (!m || !canvasRef.current) return
    const ctx = canvasRef.current.getContext('2d')
    if (chartRef.current) chartRef.current.destroy()

    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['% Generic', '% Antibiotic (Rx)', '% Injection (Rx)', '% EML'],
        datasets: [{
          label: 'WHO Indicators (MVP)',
          data: [m.percent_generic, m.percent_antibiotic_prescriptions, m.percent_injection_prescriptions, m.percent_eml],
          backgroundColor: ['#1f6feb', '#faad14', '#722ed1', '#52c41a']
        }]
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true, max: 100 } }
      }
    })
  }, [m])

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2>WHO Indicators</h2>
        <button onClick={load}>Refresh</button>
      </div>

      {err && <div className="error">{err}</div>}
      {!m && !err && <div className="muted">Loading…</div>}

      {m && (
        <>
          <div className="kv">
            <div className="muted">Total prescriptions</div><div>{m.total_prescriptions}</div>
            <div className="muted">Total drugs</div><div>{m.total_drugs}</div>
            <div className="muted">Avg drugs / prescription</div><div>{m.avg_drugs_per_prescription}</div>
          </div>
          <canvas ref={canvasRef} height="120"></canvas>
          <p className="muted" style={{ marginTop: 8 }}>
            Reminder: “generic”/“EML” here are demo heuristics. Swap in real drug vocabularies for accuracy.
          </p>
        </>
      )}
    </div>
  )
}
