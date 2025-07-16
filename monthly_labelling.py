import pandas as pd
import json
import os


def save_monthly_label(app, selected_month, evidence, categories, reason):
    """Save monthly flare label"""
    if not selected_month:
        return "Please select a month", ""
    
    if evidence == "Yes" and not categories:
        return "Please select at least one category when evidence is Yes", ""
    
    try:
        # Convert month to period
        selected_period = pd.to_datetime(selected_month, format='%B %Y').to_period('M')
        
        # Convert readable labels to internal format
        label_to_internal = {
            'Ambulatory Visit': 'ambulatory_visit',
            'Lab Test': 'lab_test', 
            'Prescription': 'prescription',
            'Physician Claim': 'physician_claim',
            'Hospital Admission': 'hospital_admission',
            'Imaging': 'imaging'
        }
        internal_categories = [label_to_internal.get(cat, cat.lower().replace(' ', '_')) for cat in categories] if categories else []
        
        # Load existing monthly labels
        monthly_labels = load_monthly_labels(app)
        
        # Update or add label for this month
        monthly_labels[str(selected_period)] = {
            "evidence": evidence,
            "categories": internal_categories,
            "reason": reason or ""
        }
        
        # Save monthly labels
        save_monthly_labels(app, monthly_labels)
        
        # Update labels info display
        labels_info = get_monthly_labels_info(app)
        
        return f"Label saved for {selected_month}: Evidence={evidence}", labels_info
        
    except Exception as e:
        return f"Failed to save label: {str(e)}", ""


def clear_monthly_label(app, selected_month):
    """Clear label for selected month"""
    if not selected_month:
        return "Please select a month", ""
    
    try:
        selected_period = pd.to_datetime(selected_month, format='%B %Y').to_period('M')
        
        monthly_labels = load_monthly_labels(app)
        
        if str(selected_period) in monthly_labels:
            del monthly_labels[str(selected_period)]
            save_monthly_labels(app, monthly_labels)
        
        labels_info = get_monthly_labels_info(app)
        
        return f"Label cleared for {selected_month}", labels_info
        
    except Exception as e:
        return f"Failed to clear label: {str(e)}", ""


def load_monthly_labels(app):
    """Load monthly labels from JSON file"""
    if app.current_patient_id is None:
        return {}
    
    save_file = f'patient_{app.current_patient_id}_monthly_labels.json'
    
    if os.path.exists(save_file):
        try:
            with open(save_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading monthly labels: {e}")
            return {}
    return {}


def save_monthly_labels(app, labels):
    """Save monthly labels to JSON file"""
    if app.current_patient_id is None:
        return
    
    try:
        save_file = f'patient_{app.current_patient_id}_monthly_labels.json'
        with open(save_file, 'w') as f:
            json.dump(labels, f, indent=2)
    except Exception as e:
        print(f"Error saving monthly labels: {e}")


def get_monthly_labels_info(app):
    """Get formatted string of all monthly labels"""
    monthly_labels = load_monthly_labels(app)
    
    if not monthly_labels:
        return "No labels saved yet"
    
    info_lines = []
    label_mapping = {
        'ambulatory_visit': 'Ambulatory Visit',
        'lab_test': 'Lab Test',
        'prescription': 'Prescription', 
        'physician_claim': 'Physician Claim',
        'hospital_admission': 'Hospital Admission',
        'imaging': 'Imaging'
    }
    
    for month_period, label_data in sorted(monthly_labels.items()):
        try:
            period = pd.Period(month_period)
            month_str = period.strftime('%B %Y')
            evidence = label_data.get('evidence', 'No')
            
            line = f"{month_str}: {evidence}"
            
            if evidence == "Yes":
                categories = label_data.get('categories', [])
                if categories:
                    readable_cats = [label_mapping.get(cat, cat) for cat in categories]
                    line += f" ({', '.join(readable_cats)})"
                
                reason = label_data.get('reason', '')
                if reason:
                    line += f" - {reason}"
            
            info_lines.append(line)
            
        except Exception as e:
            print(f"Error formatting label: {e}")
            continue
    
    return "\n".join(info_lines)


def get_monthly_labels_list(app):
    """Get list of months with labels for editing dropdown"""
    monthly_labels = load_monthly_labels(app)
    if not monthly_labels:
        return []
    
    month_list = []
    for month_period_str in sorted(monthly_labels.keys()):
        try:
            period = pd.Period(month_period_str)
            month_str = period.strftime('%B %Y')
            month_list.append(month_str)
        except Exception as e:
            print(f"Error formatting month: {e}")
            continue
    
    return month_list


def load_label_for_edit(app, edit_month):
    """Load existing label for editing"""
    if not edit_month:
        return "No", [], "", "Please select a month to edit"
    
    try:
        selected_period = pd.to_datetime(edit_month, format='%B %Y').to_period('M')
        monthly_labels = load_monthly_labels(app)
        
        if str(selected_period) in monthly_labels:
            label_data = monthly_labels[str(selected_period)]
            evidence = label_data.get('evidence', 'No')
            categories = label_data.get('categories', [])
            reason = label_data.get('reason', '')
            
            # Convert internal categories to readable labels
            internal_to_label = {
                'ambulatory_visit': 'Ambulatory Visit',
                'lab_test': 'Lab Test',
                'prescription': 'Prescription',
                'physician_claim': 'Physician Claim',
                'hospital_admission': 'Hospital Admission',
                'imaging': 'Imaging'
            }
            readable_categories = [internal_to_label.get(cat, cat.replace('_', ' ').title()) for cat in categories]
            
            return evidence, readable_categories, reason, f"Loaded label for {edit_month}"
        else:
            return "No", [], "", f"No label found for {edit_month}"
            
    except Exception as e:
        return "No", [], "", f"Failed to load label: {str(e)}"


def delete_monthly_label(app, edit_month):
    """Delete label for selected month"""
    if not edit_month:
        return "Please select a month to delete", ""
    
    try:
        selected_period = pd.to_datetime(edit_month, format='%B %Y').to_period('M')
        monthly_labels = load_monthly_labels(app)
        
        if str(selected_period) in monthly_labels:
            del monthly_labels[str(selected_period)]
            save_monthly_labels(app, monthly_labels)
            labels_info = get_monthly_labels_info(app)
            return f"Label deleted for {edit_month}", labels_info
        else:
            return f"No label found for {edit_month}", get_monthly_labels_info(app)
            
    except Exception as e:
        return f"Failed to delete label: {str(e)}", get_monthly_labels_info(app)


# Add these methods to the PatientTimelineApp class
def add_monthly_labelling_methods(app_class):
    """Add monthly labelling methods to the app class"""
    
    def save_monthly_label_method(self, selected_month, evidence, categories, reason):
        return save_monthly_label(self, selected_month, evidence, categories, reason)
    
    def clear_monthly_label_method(self, selected_month):
        return clear_monthly_label(self, selected_month)
    
    def load_monthly_labels_method(self):
        return load_monthly_labels(self)
    
    def save_monthly_labels_method(self, labels):
        return save_monthly_labels(self, labels)
    
    def get_monthly_labels_info_method(self):
        return get_monthly_labels_info(self)
    
    def get_monthly_labels_list_method(self):
        return get_monthly_labels_list(self)
    
    def load_label_for_edit_method(self, edit_month):
        return load_label_for_edit(self, edit_month)
    
    def delete_monthly_label_method(self, edit_month):
        return delete_monthly_label(self, edit_month)
    
    # Add methods to class
    app_class.save_monthly_label = save_monthly_label_method
    app_class.clear_monthly_label = clear_monthly_label_method
    app_class.load_monthly_labels = load_monthly_labels_method
    app_class.save_monthly_labels = save_monthly_labels_method
    app_class.get_monthly_labels_info = get_monthly_labels_info_method
    app_class.get_monthly_labels_list = get_monthly_labels_list_method
    app_class.load_label_for_edit = load_label_for_edit_method
    app_class.delete_monthly_label = delete_monthly_label_method