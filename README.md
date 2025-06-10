**Patient Timeline Viewer (Web Version)**

Part of the [`ibd-data-timeline-app`](https://github.com/phairlab/ibd-data-labelling-app)
This repository contains the Gradio-based web version of the IBD Timeline Viewer, designed for visualizing longitudinal patient event data and annotating disease flare-up periods interactively.


**Overview**

The Patient Timeline Viewer is an interactive web application for researchers and clinicians to:

* Load or generate patient event data
* Visualize timelines with detailed hover info
* Annotate, edit, and save IBD flare periods
* Export and import patient data in CSV or Excel formats

This version is intended for use via a browser and is not packaged as a standalone desktop application.

🚀 Getting Started

1. Clone the Repository

```bash
git clone https://github.com/phairlab/ibd-data-labelling-app.git
cd ibd-data-labelling-webapp
```

2. Install Dependencies

```bash
pip install -r requirements.txt
```

> Required packages include: `gradio`, `plotly`, `pandas`, `numpy`, etc.

3. Launch the App

```bash
webapp app.py
```

The app will launch in your default browser.



## 🧠 Features

**Data Loading**

  * Upload `.csv` or `.xlsx` patient datasets
  * Or generate synthetic test data with configurable record counts

**Interactive Timeline**

  * Events are visualized using Plotly with detailed hover info
  * Flare periods are shown with red overlays and triangle markers

**Flare Management**

  * Add, edit, delete, and persist flare-up periods per patient
  * Flare annotations saved to local JSON files

**Export Options**

  * Export the loaded/generated dataset to CSV or Excel

**User Guide Built-In**

  * Full usage instructions available under the "User Guide" tab


## 📁 Data Format

**Required Columns:**

* `patient_id`: Unique patient identifier
* `start_date`: Event start date (YYYY-MM-DD)
* `end_date`: Event end date (YYYY-MM-DD)
* `event_type`: Type of medical event

**Optional Columns:**

* `event_info`: JSON-encoded string with extra details (e.g., age, sex, notes)
* `source_dataset`: Source system for the event
* `ibd_related`: Boolean indicating whether event is IBD-related


## 🖼 Example Use Cases

* Visualize medical histories across multiple data sources
* Manually annotate periods of IBD activity ("flares")
* Export cleaned datasets for further research
* Share the tool with clinicians via a browser-based interface


## 🌐 Differences from the Standalone App

This is the **web-hosted version** of the IBD Timeline Viewer.
For a **desktop executable version**, see the standalone app implementation in the repo called ibd-data-labelling-app


