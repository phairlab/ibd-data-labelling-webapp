# Patient Timeline Viewer (Web Application)

Part of the [`ibd-data-timeline-app`](https://github.com/phairlab/ibd-data-labelling-app) ecosystem

An advanced web-based application for visualizing longitudinal patient event data with interactive timeline visualization, IBD flare annotation, and multi-user access control. Designed for researchers and clinicians working with complex medical datasets.

## 🌟 Key Features

### 📊 **Advanced Timeline Visualization**
- Interactive Plotly-based timelines with zoom, pan, and hover capabilities
- Color-coded event types with smart hover tooltips
- Intelligent handling of same-day events (especially lab tests)
- Real-time chart updates and filtering

### 🎯 **IBD Event Filtering**
- **All Events**: View complete medical history
- **IBD Related Only**: Focus on IBD-specific events
- **Non-IBD Related Only**: View non-IBD medical events
- Real-time filtering without page reloads

### 🔥 **Flare Period Management**
- Add, edit, and delete IBD flare periods with visual annotations
- Red shaded regions and triangular markers for flare visualization
- Persistent storage with automatic save/load functionality
- Detailed flare reasoning and date tracking

### 👥 **Multi-User Access Control**
- Command-line based patient group access
- Secure patient data segregation
- Role-based access (researcher, clinician, admin)
- Custom patient cohort definitions

### 🔄 **Intelligent Data Processing**
- Automatic CSV file loading from specified directories
- Smart text wrapping for long medical descriptions
- Multiple lab test separation for same-day events
- Robust error handling and fallback systems

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/phairlab/ibd-data-labelling-app.git
cd ibd-data-labelling-webapp
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

**Required packages:**
- `gradio` - Web interface framework
- `plotly` - Interactive plotting
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `argparse` - Command-line argument parsing

### 3. Prepare Your Data
Ensure your CSV files are located in:
```
/data/external_ps/baumgart/BAUMGART_SHARED/Baumgart_IBD/Sacha/ibd_activity_viewer/data
```

Files should contain "events" in the filename (e.g., `patient_events_2024.csv`)

### 4. Launch with Access Control

#### **Research Teams (Predefined Groups)**
```bash
# Group A: Patients 1-100
python app.py group-a

# Group B: Patients 101-200
python app.py group-b

# Group C: Patients 201-300
python app.py group-c
```

#### **Custom Patient Cohorts**
```bash
# Custom range with naming
python app.py custom --start 50 --end 150 --name "Pediatric Cohort"

# Simple custom range
python app.py custom --start 1 --end 25
```

#### **Special Access Modes**
```bash
# Administrator access (all patients)
python app.py admin

# Development mode (sample data)
python app.py dev --patients 100
```

The application will launch in your default browser with access restricted to your specified patient group.

## 📋 Data Format Requirements

### **Required Columns**
| Column | Type | Description |
|--------|------|-------------|
| `patient_id` | Integer | Unique patient identifier |
| `start_date` | Date | Event start date (YYYY-MM-DD) |
| `end_date` | Date | Event end date (YYYY-MM-DD) |
| `event_type` | String | Type of medical event |
| `ibd_related` | Boolean | Whether event is IBD-related (True/False) |

### **Optional Columns**
| Column | Type | Description |
|--------|------|-------------|
| `event_info` | JSON String | Additional event details (age, sex, notes) |
| `source_dataset` | String | Data source identifier (CLAIMS, LAB, DAD, etc.) |

### **Example Data Structure**
```csv
patient_id,start_date,end_date,event_type,ibd_related,event_info,source_dataset
101,2024-01-15,2024-01-15,lab_test,True,"{""test_type"":""CBC"",""result"":""normal""}",LAB
101,2024-01-20,2024-01-22,hospitalization,True,"{""admission_reason"":""IBD flare""}",DAD
```

## 🎛️ User Interface Guide

### **Timeline Viewer Tab**
1. **Patient Selection**: Choose from your accessible patient cohort
2. **IBD Filter**: Select event types to display
3. **Interactive Timeline**: 
   - Hover for detailed event information
   - Zoom and pan for timeline navigation
   - Color-coded event types

### **Flare Management Panel**
1. **Add Flares**: Enter date range and reason
2. **Edit Existing**: Select and modify flare periods  
3. **Visual Feedback**: Red overlays show flare periods
4. **Persistent Storage**: Auto-save/load per patient

### **Data Overview Tab**
- View current access permissions
- Export filtered datasets
- Reload data from directory

## 🔧 Advanced Features

### **Smart Lab Test Handling**
Multiple lab tests on the same day are automatically separated with 2-hour offsets for individual visualization while maintaining chronological accuracy.

### **Intelligent Text Wrapping**
Long medical descriptions are automatically wrapped in hover tooltips for better readability without horizontal scrolling.

### **Real-Time Updates**
All filtering, flare management, and chart interactions update immediately without page reloads.

### **Color-Coded Visualization**
- Different event types have distinct colors
- Hover tooltips match event bar colors
- Flare periods use consistent red highlighting

## 🛡️ Security & Access Control

### **Patient Data Protection**
- Command-line access control prevents unauthorized patient access
- Data filtering at application level
- Secure patient ID range enforcement

### **Team-Based Access**
```bash
# Clinical team
python app.py group-a

# Research team  
python app.py group-b

# Analysis team
python app.py custom --start 200 --end 300 --name "Analysis Cohort"
```

## 📈 Use Cases

### **Clinical Research**
- Longitudinal patient history visualization
- IBD flare period identification and annotation
- Multi-source medical data integration
- Cohort-specific analysis

### **Clinical Practice**
- Patient timeline review
- Flare pattern identification
- Treatment timeline visualization
- Multi-disciplinary team collaboration

### **Data Analysis**
- Dataset preparation and cleaning
- Temporal pattern identification
- Export prepared datasets for statistical analysis

## 🔍 Troubleshooting

### **Common Issues**

**No patients visible:**
- Verify your access command includes patients in the data range
- Check data directory contains properly formatted CSV files

**Events not showing:**
- Check IBD filter setting matches desired event types
- Verify `ibd_related` column contains proper boolean values

**Flares not saving:**
- Ensure dates are in YYYY-MM-DD format
- Verify end date is after start date

**Performance issues:**
- Large datasets may require filtering to specific patient ranges
- Use development mode for testing with sample data


## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create a Pull Request


## 🙏 Acknowledgments

- Built with [Gradio](https://gradio.app/) for the web interface
- Visualization powered by [Plotly](https://plotly.com/python/)
- Part of the IBD research toolkit ecosystem

## 📞 Support

For issues, questions, or feature requests, please open an issue on GitHub or contact the development team.

---

**Note**: This is the web-hosted version of the IBD Timeline Viewer. For the desktop executable version, see the [standalone app implementation](https://github.com/phairlab/ibd-data-labelling-app).
