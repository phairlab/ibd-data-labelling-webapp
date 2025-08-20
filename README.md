# 🏥 Patient Timeline Viewer

> **A comprehensive medical timeline visualization and flare management tool for IBD (Inflammatory Bowel Disease) research**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Gradio](https://img.shields.io/badge/interface-gradio-orange.svg)](https://gradio.app/)

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Data Format](#-data-format)
- [Architecture](#-architecture)
- [User Interface](#-user-interface)
- [Access Control](#-access-control)
- [File Structure](#-file-structure)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)
- [API Reference](#-api-reference)
- [Contributing](#-contributing)
- [License](#-license)

## Overview

The **Patient Timeline Viewer** is a sophisticated web application designed specifically for medical researchers and clinicians working with IBD patients. It provides powerful visualization tools for exploring patient medical events over time and enables efficient labeling of disease flare periods.

### What This Tool Does

- **Visualizes Patient Timelines**: Interactive charts showing medical events chronologically
- **Filters Medical Data**: Separate IBD-related from general medical events
- **Labels Disease Flares**: Month-by-month annotation of disease activity
- **Manages Access Control**: Team-based patient data access
- **Exports Data**: Save timelines and labels for further analysis

### Who Should Use This

- **Medical Researchers** studying IBD patterns
- **Clinicians** reviewing patient histories
- **Data Analysts** working with medical timelines
- **Students** learning medical data visualization

## Features

### Interactive Timeline Visualization
- **Gantt-style charts** showing events over time
- **Hover tooltips** with detailed event information
- **Zoom and pan** capabilities for detailed exploration
- **Colour-coded events** by medical category
- **Smart lab test spacing** for same-day multiple tests

### Advanced Flare Labeling
- **Monthly labeling system** for disease activity
- **Category-based evidence** linking flares to event types
- **Reason documentation** for clinical notes
- **Visual flare indicators** on timelines
- **Persistent storage** of all labels in JSON format

### Team-Based Access Control
- **Patient group isolation** for research teams
- **Command-line access control** for different user roles
- **Custom patient ranges** for specific studies
- **Admin access** for supervisors

### Data Management
- **Automatic data loading** from CSV files
- **Real-time filtering** by IBD relevance
- **Export capabilities** to CSV/Excel
- **Cross-tab synchronization** between views

### User-Friendly Interface
- **Three-tab layout**: Overview, Timeline, Labeling
- **Clean, medical-grade design** with professional styling
- **Responsive layout** for different screen sizes
- **Comprehensive help documentation**

## Installation

### Prerequisites

Make sure you have Python 3.8 or higher installed:

```bash
python --version
# Should show: Python 3.8.x or higher
```

### Step 1: Download the Application

```bash
# Create a new directory for the project
mkdir patient-timeline-viewer
cd patient-timeline-viewer

# Download all four files (main.py, patient_timeline_webapp.py, monthly_labelling.py, timeline_visualization.py)
# Place them in the patient-timeline-viewer directory
```

### Step 2: Install Dependencies

```bash
# Install required Python packages
pip install gradio pandas plotly numpy openpyxl

# Or install from requirements.txt 
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
# Test the installation with sample data
python main.py dev --patients 5
```

If successful, you should see:
```
Running on local URL:  http://127.0.0.1:7860
```

## Quick Start

### 1. **Launch with Sample Data** (Recommended for first-time users)

```bash
python main.py dev --patients 10
```

This creates 10 sample patients with realistic medical data for testing.

### 2. **Open Your Web Browser**

Navigate to: `http://127.0.0.1:7860`

### 3. **Explore the Interface**

1. **Data Overview Tab**: Check data loading status
2. **Timeline Viewer Tab**: Select a patient and view their timeline
3. **Labelling Mode Tab**: Practice labeling disease flares

### 4. **Try Key Features**

- **Select a patient** from the dropdown
- **Filter events** using IBD/Non-IBD options
- **Hover over events** to see detailed information
- **Create a monthly label** in the Labelling Mode tab

## Usage

### Command Line Options

The application supports multiple access modes through command-line arguments:

#### Development Mode
```bash
# Start with sample data (great for testing)
python main.py dev --patients 20
```

#### Research Team Access
```bash
# Group A: Patients 1-100
python main.py group-a

# Group B: Patients 101-200
python main.py group-b

# Group C: Patients 201-300
python main.py group-c
```

#### Custom Patient Range
```bash
# Define your own patient range
python main.py custom --start 50 --end 150 --name "Pediatric Study"
```

#### Administrator Access
```bash
# Access all patients (requires admin privileges)
python main.py admin
```

### Working with Real Data

#### 1. **Data Directory Setup**

The application looks for data in:
```
/data/external_ps/baumgart/BAUMGART_SHARED/Baumgart_IBD/Sacha/ibd_activity_viewer
```

#### 2. **Expected File**

- **Filename**: `selected_events_mia_patients.csv`
- **Format**: CSV with specific column structure (see Data Format section)

#### 3. **Loading Real Data**

```bash
# Launch with your assigned patient group
python main.py group-a  # or group-b, group-c, etc.
```

## Data Format

### Required CSV Structure

Your data file must contain these columns:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `patient_id` | Integer | Unique patient identifier | `12345` |
| `start_date` | Date | Event start date | `2023-01-15` |
| `end_date` | Date | Event end date | `2023-01-15` |
| `event_type` | String | Type of medical event | `ambulatory_visit` |
| `ibd_related` | Boolean | Whether event is IBD-related | `True` |

### Optional Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `event_info` | JSON String | Additional event details | `{"Patient Age": 45, "Diagnosis": "Crohn's"}` |
| `source_dataset` | String | Data source identifier | `CLAIMS` |

### Supported Event Types

The application recognizes these medical event categories:

- **`ambulatory_visit`** → Ambulatory Visit
- **`lab_test`** → Lab Test
- **`prescription`** → Prescription
- **`physician_claim`** → Physician Claim
- **`hospital_admission`** → Hospital Admission
- **`imaging`** → Imaging
- **`hospitalization`** → Hospitalization
- **`medication_change`** → Medication Change

### Example Data Row

```csv
patient_id,start_date,end_date,event_type,ibd_related,event_info,source_dataset
12345,2023-01-15,2023-01-15,ambulatory_visit,True,"{""Patient Age"": 45, ""Diagnosis"": ""Crohn's Disease""}",CLAIMS
```

## Architecture

### System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │◄──►│   Gradio UI     │◄──►│  Application    │
│                 │    │                 │    │     Logic       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   Data Storage  │
                                               │   (CSV/JSON)    │
                                               └─────────────────┘
```

### Component Architecture

```
main.py
├── UI Interface & Event Handling
├── Command Line Argument Processing
└── Application Orchestration

patient_timeline_webapp.py
├── Core Application Logic
├── Data Loading & Management
├── Patient Filtering
└── Timeline Coordination

monthly_labelling.py
├── Flare Label Management
├── JSON Persistence
├── Label Validation
└── Edit Operations

timeline_visualization.py
├── Plotly Chart Creation
├── Visual Styling
├── Hover Data Processing
└── Interactive Features
```

## User Interface

### Tab 1: Data Overview

**Purpose**: Monitor data loading status and export capabilities

**Features**:
- **Data Status Display**: Shows loaded patient count and date ranges
- **Reload Functionality**: Refresh data from source files
- **Export Options**: Save data to CSV or Excel formats
- **Patient Range Information**: Current access permissions

**When to Use**:
- ✅ First time loading the application
- ✅ Troubleshooting data loading issues
- ✅ Exporting data for external analysis
- ✅ Verifying patient access permissions

### Tab 2: Timeline Viewer 📈

**Purpose**: Interactive visualization of patient medical timelines

**Layout**:
```
┌─────────────────┬─────────────────────────────────────────┐
│  Patient        │  Timeline Chart                         │
│  Selection      │  ┌─────────────────────────────────────┐│
│  ┌───────────┐  │  │        Interactive Timeline         ││
│  │Patient ID │  │  │                                     ││
│  └───────────┘  │  │  [IBD Filter] [Refresh Chart]       ││
│  [Load Button]  │  └───────────────────────────────────── │
└─────────────────┴─────────────────────────────────────────┘
```

**Controls**:
- **Patient Dropdown**: Select specific patient
- **IBD Filter**: Show All/IBD Only/Non-IBD events
- **Load Timeline**: Generate visualization
- **Refresh Chart**: Update with latest data

**Chart Features**:
- **Gantt-style bars** for each medical event
- **Color coding** by event type
- **Hover tooltips** with detailed information
- **Zoom and pan** for detailed exploration
- **Flare indicators** (red rectangles for monthly flares)

### Tab 3: Labelling Mode 

**Purpose**: Efficient monthly flare labeling with timeline context

**Layout**:
```
┌─────────────────┬─────────────────────────────────────────┐
│  Controls       │  Monthly Timeline                       │
│  ┌───────────┐  │  ┌─────────────────────────────────────┐│
│  │Patient ID │  │  │  [◀ Prev] [Next ▶]                  ││
│  └───────────┘  │  │                                     ││
│                 │  │      Monthly View Timeline          ││
│  ┌───────────┐  │  │                                     ││
│  │Month      │  │  │                                     ││
│  │Selection  │  │  │                                     ││
│  └───────────┘  │  └─────────────────────────────────────┘│
│                 │                                         │
│  Flare Labels   │                                         │
│  ┌───────────┐  │                                         │
│  │Evidence?  │  │                                         │
│  │Categories │  │                                         │
│  │Reason     │  │                                         │
│  └───────────┘  │                                         │
└─────────────────┴─────────────────────────────────────────┘
```

**Workflow**:
1. **Load Patient**: Select patient for labeling
2. **Choose Month**: Navigate to specific month
3. **View Timeline**: See events for that month or other months for context 
4. **Label Flare**: Mark evidence and categories
5. **Save Label**: Store annotation permanently

**Controls**:
- **Month Navigation**: Previous/Next buttons + dropdown
- **Evidence Radio**: Yes/No flare evidence
- **Category Selection**: Multi-select relevant event types
- **Reason Field**: Optional text documentation
- **Save/Clear**: Label management buttons

## Access Control

### Team-Based Patient Access

The application implements strict access control to ensure research teams only see their assigned patients:

#### Group A (Patients 1-100)
```bash
python main.py group-a
# Access: Patients 1-100
# Team: Early diagnosis research
```

#### Group B (Patients 101-200)
```bash
python main.py group-b
# Access: Patients 101-200
# Team: Treatment response analysis
```

#### Group C (Patients 201-300)
```bash
python main.py group-c
# Access: Patients 201-300
# Team: Long-term outcomes study
```

### Custom Access Ranges

For specific studies or sub-analyses:

```bash
python main.py custom --start 50 --end 150 --name "Pediatric Cohort"
# Access: Patients 50-150
# Custom name appears in UI
```

### Administrator Access

For supervisors and data managers:

```bash
python main.py admin
# Access: All patients
# Full dataset visibility
```

### Security Features

- **Command-line enforcement**: Access defined at startup
- **UI restrictions**: Only assigned patients appear in dropdowns
- **Data filtering**: Automatic patient range application
- **Audit logging**: Access patterns recorded in console

## 📁 File Structure

```
ibd-data-labelling-webapp
├── main.py                     # Application entry point & UI
├── patient_timeline_webapp.py  # Core application logic
├── monthly_labelling.py        # Flare labeling functionality
├── timeline_visualization.py   # Chart creation & visualization
├── README.md                   # This documentation
├── requirements.txt            # Python dependencies
└── data/                       # Data directory, repo path: '/data/external_ps/baumgart/BAUMGART_SHARED/Baumgart_IBD/Sacha/ibd_activity_viewer'
    └── selected_events_mia_patients.csv  # Selected 10 patients' data
```

### File Responsibilities

#### `main.py` (Entry Point)
```python
# What it does:
- Command-line argument processing
- Gradio interface creation
- Event handler setup
- Application launch coordination

# Key functions:
- parse_arguments()        # Process command line options
- create_app_with_args()   # Initialize with user permissions
- create_interface()       # Build Gradio UI
```

#### `patient_timeline_webapp.py` (Core Logic)
```python
# What it does:
- Data loading and management
- Patient filtering and selection
- Timeline coordination
- Export functionality

# Key class: PatientTimelineApp
- auto_load_data()         # Load CSV data automatically
- load_patient_timeline()  # Generate patient timeline
- apply_patient_filter()   # Enforce access control
- export_data()            # Save data to files
```

#### `monthly_labelling.py` (Flare Management)
```python
# What it does:
- Monthly flare label storage
- JSON file persistence
- Label validation and editing
- Category management

# Key functions:
- save_monthly_label()     # Store flare annotation
- load_monthly_labels()    # Retrieve saved labels
- delete_monthly_label()   # Remove annotations
- get_monthly_labels_info() # Format for display
```

#### `timeline_visualization.py` (Charts)
```python
# What it does:
- Plotly chart creation
- Visual styling and theming
- Hover data processing
- Interactive features

# Key functions:
- create_main_timeline()   # Full patient timeline
- create_monthly_timeline() # Single month view
- add_flares_to_chart()    # Flare visualization
- process_lab_test_data()  # Handle multiple same-day tests
```

## 🛠️ Development

### Setting Up Development Environment

```bash
# 1. Clone/download the project
git clone <repository-url>
cd patient-timeline-viewer

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run in development mode
python main.py dev --patients 50
```

### Code Organization Principles

#### 1. **Separation of Concerns**
- **UI logic** isolated in `main.py`
- **Business logic** in `patient_timeline_webapp.py`
- **Specialized features** in dedicated modules

#### 2. **Functional Programming**
- **Pure functions** where possible
- **Minimal side effects**
- **Clear input/output contracts**

#### 3. **Error Handling**
- **Graceful degradation** for missing data
- **User-friendly error messages**
- **Comprehensive logging**

### Making Changes

#### Adding New Event Types
1. Update `get_label_mapping()` in `timeline_visualization.py`
2. Add to category choices in `main.py`
3. Update documentation

#### Modifying Chart Appearance
1. Edit styling in `timeline_visualization.py`
2. Update CSS in `main.py` for UI elements
3. Test with different data sizes

#### Adding New Access Groups
1. Extend `parse_arguments()` in `main.py`
2. Add new command option
3. Update help documentation

### Testing

#### Manual Testing Checklist

- [ ] **Data Loading**: CSV files load correctly
- [ ] **Patient Selection**: Dropdown populates properly
- [ ] **Timeline Generation**: Charts render without errors
- [ ] **Flare Labeling**: Labels save and load correctly
- [ ] **Access Control**: Patient filtering works
- [ ] **Export Functions**: CSV/Excel export succeeds

#### Common Test Scenarios

```bash
# Test with small dataset
python main.py dev --patients 5

# Test access control
python main.py group-a

# Test custom ranges
python main.py custom --start 1 --end 10 --name "Test"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. **Application Won't Start**

**Error**: `ModuleNotFoundError: No module named 'gradio'`
```bash
# Solution: Install dependencies
pip install gradio pandas plotly numpy openpyxl
```

**Error**: `ModuleNotFoundError: No module named 'patient_timeline_webapp'`
```bash
# Solution: Ensure all files are in the same directory
ls -la
# Should show: main.py, patient_timeline_webapp.py, monthly_labelling.py, timeline_visualization.py
```

#### 2. **No Data Loading**

**Problem**: "No data loaded" appears in interface

**Solutions**:
1. **Check data file location**:
   ```bash
   # Expected location:
   /data/external_ps/baumgart/BAUMGART_SHARED/Baumgart_IBD/Sacha/ibd_activity_viewer/data/selected_events_mia_patients.csv
   ```

2. **Use development mode**:
   ```bash
   python main.py dev --patients 10
   ```

3. **Verify file format**:
   - CSV file with proper column names
   - Date format: YYYY-MM-DD
   - Boolean values: True/False (not 1/0)

#### 3. **Patient Access Issues**

**Problem**: "No patients visible" in dropdown

**Solutions**:
1. **Check patient ID ranges**:
   ```bash
   # Ensure your data has patients in the expected range
   python main.py admin  # See all patients
   ```

2. **Verify command usage**:
   ```bash
   # Correct usage:
   python main.py group-a  # NOT: python main.py group-a.py
   ```

#### 4. **Chart Display Problems**

**Problem**: Charts appear blank or overlapping

**Solutions**:
1. **Clear browser cache**
2. **Refresh the page**
3. **Try different patient**:
   ```bash
   # Use patients with more data
   python main.py dev --patients 20
   ```

#### 5. **Labels Not Saving**

**Problem**: Monthly labels disappear after restart

**Solutions**:
1. **Check write permissions** in application directory
2. **Verify patient is loaded** before labeling
3. **Check file creation**:
   ```bash
   ls -la patient_*_monthly_labels.json
   ```

#### 6. **Performance Issues**

**Problem**: Application runs slowly

**Solutions**:
1. **Reduce patient count** in development mode
2. **Filter data** by date range
3. **Use smaller datasets** for testing


### Getting Help

1. **Check console output** for error messages
2. **Verify all dependencies** are installed
3. **Test with sample data** first
4. **Check file permissions** for data directories
5. **Consult this README** for configuration details

## API Reference

### PatientTimelineApp Class

#### Constructor
```python
PatientTimelineApp(patient_range=None, group_name="Default")
```

**Parameters**:
- `patient_range`: Tuple of (start_id, end_id) for patient filtering
- `group_name`: Display name for the patient group

#### Core Methods

##### Data Management
```python
def auto_load_data(self)
```
Automatically loads patient data from CSV files or generates sample data.

```python
def get_patient_choices(self)
```
Returns list of available patient IDs as strings.

```python
def export_data(self, format_choice)
```
Exports current data to CSV or Excel format.

##### Timeline Operations
```python
def load_patient_timeline(self, patient_id, ibd_filter="All Events")
```
Loads and creates timeline visualization for specified patient.

**Parameters**:
- `patient_id`: String representation of patient ID
- `ibd_filter`: "All Events", "IBD Related Only", or "Non-IBD Related Only"

**Returns**: (figure, status_message, chart_info)

##### Monthly Labeling
```python
def save_monthly_label(self, selected_month, evidence, categories, reason)
```
Saves monthly flare label to JSON file.

**Parameters**:
- `selected_month`: Month string in "Month YYYY" format
- `evidence`: "Yes" or "No"
- `categories`: List of event type categories
- `reason`: Optional text description

### Key Functions

#### Timeline Visualization
```python
def create_main_timeline(app)
```
Creates full patient timeline with all events and flares.

```python
def create_monthly_timeline(app, selected_month, view_offset=0)
```
Creates focused monthly timeline view.

#### Data Processing
```python
def process_lab_test_data(data)
```
Handles multiple lab tests on same day with time offsets.

```python
def create_hover_data(data)
```
Generates rich hover tooltips for timeline events.

### Event Handlers

#### UI Events
- `load_timeline_btn.click()`: Load patient timeline
- `save_label_btn.click()`: Save monthly flare label
- `month_dropdown.change()`: Update monthly view
- `ibd_filter.change()`: Filter timeline events

#### Data Events
- `reload_data_btn.click()`: Refresh data from files
- `export_btn.click()`: Export data to file

## Contributing

### Development Workflow

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-feature`
3. **Make changes** following code style guidelines
4. **Test thoroughly** with sample data
5. **Submit pull request** with detailed description

### Code Style Guidelines

#### Python Standards
- Follow **PEP 8** for code formatting
- Use **descriptive variable names**
- Add **docstrings** for all functions
- Include **type hints** where applicable

#### Documentation
- Update **README.md** for new features
- Add **inline comments** for complex logic
- Include **examples** for new functionality

#### Testing
- Test with **multiple patient counts**
- Verify **access control** works correctly
- Check **data export** functionality
- Ensure **UI responsiveness**

### Reporting Issues

When reporting bugs, please include:

1. **Command used** to start application
2. **Error messages** from console
3. **Steps to reproduce** the issue
4. **Expected vs actual** behavior
5. **System information** (OS, Python version)

### Feature Requests

For new features, please describe:

1. **Use case** and motivation
2. **Proposed solution** or approach
3. **Alternative approaches** considered
4. **Impact on existing** functionality


---

## 🎉 Quick Reference Card

### Essential Commands
```bash
# Start with sample data
python main.py dev --patients 10

# Research team access
python main.py group-a

# Custom patient range
python main.py custom --start 1 --end 50 --name "Study"

# Admin access
python main.py admin
```

### Key Features
- **Interactive timelines** with medical events
- **Monthly flare labeling** with categories
- **Team-based access control** for patient groups
- **Data export** to CSV/Excel formats
- **Professional medical interface**

### Support
- **Documentation**: This README
- **Bug Reports**: GitHub Issues
- **Feature Requests**: GitHub Discussions

---
