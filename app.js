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
