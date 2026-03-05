// Updated API endpoint and added proper file upload handling

const express = require('express');
const multer = require('multer');
const router = express.Router();

// Set storage engine for multer
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

// Updated API endpoint for analysis
router.post('/analyze_text', (req, res) => {
    // Code to analyze text
});

// File upload endpoint
router.post('/upload', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).send('No file uploaded.');
    }
    // Handle the uploaded file here
    res.send('File uploaded successfully.');
});

module.exports = router;