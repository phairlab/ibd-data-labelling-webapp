# ============================================================================
# MONTHLY LABELLING MODULE - FLARE MANAGEMENT SYSTEM
# ============================================================================
#
# This module handles the monthly flare labelling functionality for the 
# Patient Timeline Viewer. It allows medical professionals to:
#
# 1. Label months as having flare evidence or not
# 2. Categorize flares by medical event types
# 3. Add optional reasoning/notes for each flare
# 4. Edit and delete existing flare labels
# 5. Persist labels to JSON files for each patient
#
# The module uses a functional approach with separate functions that are
# dynamically added to the PatientTimelineApp class to maintain clean
# separation of concerns.
#
# File Format: patient_{patient_id}_monthly_labels.json
# Structure: {
#   "2023-01": {
#     "evidence": "Yes",
#     "categories": ["ambulatory_visit", "lab_test"],
#     "reason": "Elevated inflammatory markers"
#   }
# }
# ============================================================================

import pandas as pd
import json
import os

# ============================================================================
# NEW HELPER FUNCTION TO GET GROUP-SPECIFIC SAVE DIRECTORY
# ============================================================================
def get_save_directory(app):
    """
    Get the appropriate save directory based on the user's group.
    Creates the directory if it doesn't exist.
    
    Args:
        app: PatientTimelineApp instance with group_name attribute
    
    Returns:
        str: Path to the appropriate save directory
    """
    # Base directory where all flare data should be saved
    base_dir = "/data/baumgart/BAUMGART_SHARED/Baumgart_IBD/Mia/ibd-data-labelling-webapp"
    
    # Map group names to folder names
    group_folder_mapping = {
        "Group A": "groupa_saved_flares",
        "Group B": "groupb_saved_flares", 
        "Group C": "groupc_saved_flares",
        "Admin (All Patients)": "admin_saved_flares",
        "Development Mode": "dev_saved_flares"
    }
    
    # Handle custom groups
    if app.group_name not in group_folder_mapping:
        # For custom groups, create a folder based on the sanitized group name
        folder_name = app.group_name.lower().replace(" ", "_").replace("(", "").replace(")", "") + "_saved_flares"
    else:
        folder_name = group_folder_mapping[app.group_name]
    
    # Create the full path
    full_path = os.path.join(base_dir, folder_name)
    
    # Create the directory if it doesn't exist
    try:
        if not os.path.exists(full_path):
            # Create directory with group write permissions
            os.makedirs(full_path, mode=0o775, exist_ok=True)
            print(f"Created save directory: {full_path}")
            
            # Change group ownership to 'baumgart'
            import grp
            import pwd
            try:
                # Get group ID for 'baumgart'
                group_info = grp.getgrnam('baumgart')
                # Keep current user as owner, change group to 'baumgart'
                os.chown(full_path, -1, group_info.gr_gid)
                # Set group sticky bit so files inherit group
                os.chmod(full_path, 0o2775)  # 2775 = rwxrwsr-x
                print(f"Set group ownership to 'baumgart' with sticky bit")
            except Exception as e:
                print(f"Warning: Could not set group ownership: {e}")
        else:
            print(f"Using existing save directory: {full_path}")
        return full_path
    except PermissionError as e:
        print(f"ERROR: Permission denied creating directory {full_path}")
        print(f"Error details: {e}")
        print(f"Please ensure you have write permissions to: {base_dir}")
        # Fall back to current directory as last resort
        print(f"Falling back to current directory subfolder: {folder_name}")
        if not os.path.exists(folder_name):
            os.makedirs(folder_name, exist_ok=True)
        return folder_name
    except Exception as e:
        print(f"ERROR: Unexpected error creating directory {full_path}")
        print(f"Error details: {e}")
        # Fall back to current directory as last resort
        print(f"Falling back to current directory subfolder: {folder_name}")
        if not os.path.exists(folder_name):
            os.makedirs(folder_name, exist_ok=True)
        return folder_name



def save_monthly_label(app, selected_month, evidence, categories, reason):
    """
    Save or update a monthly flare label for the current patient.
    
    This function validates the input, converts human-readable categories to
    internal format, and persists the label to a JSON file. It's the main
    function called when doctors save their flare assessments.
    
    Args:
        app: PatientTimelineApp instance containing current patient context
        selected_month (str): Month in "January 2023" format
        evidence (str): "Yes" or "No" - whether flare evidence exists
        categories (list): List of readable category names (e.g., ["Lab Test"])
        reason (str): Optional text explanation for the flare assessment
    
    Returns:
        tuple: (status_message, updated_labels_info_string)
            - status_message: Success/error message for user feedback
            - updated_labels_info_string: Formatted summary of all labels
    
    Validation:
        - Requires month selection
        - If evidence="Yes", requires at least one category
        - Handles invalid date formats gracefully
    """
    # Input validation - month must be selected
    if not selected_month:
        return "Please select a month", ""
    
    # Validation - if marking as flare, must specify categories
    if evidence == "Yes" and not categories:
        return "Please select at least one category when evidence is Yes", ""
    
    try:

        # DEBUG: Print current working directory and file path
        import os
        # ========== CHANGED: Get group-specific save directory ==========
        save_dir = get_save_directory(app)
        save_file = os.path.join(save_dir, f'patient_{app.current_patient_id}_monthly_labels.json')
        full_path = os.path.abspath(save_file)
        
        print(f"\n{'='*50}")
        print(f"\n=== SAVE MONTHLY LABEL DEBUG ===")
        print(f"{'='*50}")
        print(f"Timestamp: {pd.Timestamp.now()}")
        print(f"Current Patient ID: {app.current_patient_id}")
        print(f"Group Name: {app.group_name}")  # Added group name to debug
        print(f"Save Directory: {save_dir}")     # Added save directory to debug
        print(f"Save File Name: {os.path.basename(save_file)}")
        print(f"Full Path: {full_path}")
        print(f"Directory Exists: {os.path.exists(save_dir)}")
        print(f"Directory Writable: {os.access(save_dir, os.W_OK)}")
        print(f"File Exists: {os.path.exists(save_file)}")
        if os.path.exists(save_file):
            print(f"File Writable: {os.access(save_file, os.W_OK)}")
            print(f"File Size: {os.path.getsize(save_file)} bytes")
        print(f"User: {os.environ.get('USER', 'unknown')}")
        print(f"\nData to save:")
        print(f"  Month: {selected_month}")
        print(f"  Evidence: {evidence}")
        print(f"  Categories: {categories}")
        print(f"  Reason: {reason}")
        print(f"================================\n")
        # Convert human-readable month (e.g., "January 2023") to pandas Period
        # This standardizes the date format for consistent storage
        selected_period = pd.to_datetime(selected_month, format='%B %Y').to_period('M')
        
        # Map user-friendly category names to internal database format
        # This allows the UI to show readable names while maintaining
        # consistent internal naming conventions
        label_to_internal = {
            'Ambulatory Visit': 'ambulatory_visit',     # Outpatient visits
            'Lab Test': 'lab_test',                     # Laboratory tests
            'Prescription': 'prescription',             # Medication prescriptions
            'Physician Claim': 'physician_claim',       # Insurance claims
            'Hospital Admission': 'hospital_admission', # Inpatient stays
            'Imaging': 'imaging'                        # Medical imaging
        }
        
        # Convert selected categories to internal format
        # Handle edge case where category might not be in mapping
        internal_categories = [
            label_to_internal.get(cat, cat.lower().replace(' ', '_')) 
            for cat in categories
        ] if categories else []
        
        # Load existing labels for this patient (returns empty dict if none exist)
        monthly_labels = load_monthly_labels(app)
        
        # Create/update the label entry for this specific month
        # Using string representation of period for JSON compatibility
        monthly_labels[str(selected_period)] = {
            "evidence": evidence,           # "Yes" or "No"
            "categories": internal_categories,  # List of internal category names
            "reason": reason or ""         # Empty string if no reason provided
        }
        
        # Persist the updated labels to file
        save_monthly_labels(app, monthly_labels)
        
        # Generate updated summary text for UI display
        labels_info = get_monthly_labels_info(app)
        
        # Return success message and updated labels summary
        return f"Label saved for {selected_month}: Evidence={evidence}", labels_info
        
    except Exception as e:
        # Handle any errors (date parsing, file I/O, etc.) gracefully
        return f"Failed to save label: {str(e)}", ""


def clear_monthly_label(app, selected_month):
    """
    Remove a monthly flare label for the selected month.
    
    This function deletes an existing label entry and updates the persistent
    storage. Used when doctors want to remove an incorrect or outdated assessment.
    
    Args:
        app: PatientTimelineApp instance containing current patient context
        selected_month (str): Month in "January 2023" format to clear
    
    Returns:
        tuple: (status_message, updated_labels_info_string)
            - status_message: Confirmation or error message
            - updated_labels_info_string: Updated summary of remaining labels
    """
    # Input validation
    if not selected_month:
        return "Please select a month", ""
    
    try:
        # Convert month string to standardized period format
        selected_period = pd.to_datetime(selected_month, format='%B %Y').to_period('M')
        
        # Load current labels for this patient
        monthly_labels = load_monthly_labels(app)
        
        # Remove the label if it exists (no error if it doesn't exist)
        if str(selected_period) in monthly_labels:
            del monthly_labels[str(selected_period)]
            # Save the updated labels back to file
            save_monthly_labels(app, monthly_labels)
        
        # Generate updated summary for UI
        labels_info = get_monthly_labels_info(app)
        
        return f"Label cleared for {selected_month}", labels_info
        
    except Exception as e:
        return f"Failed to clear label: {str(e)}", ""


def load_monthly_labels(app):
    """
    Load monthly labels from JSON file for the current patient.
    
    This function reads the persistent storage file for the current patient's
    monthly flare labels. Each patient has their own JSON file to maintain
    data isolation and enable easy backup/transfer of individual patient data.
    
    Args:
        app: PatientTimelineApp instance with current_patient_id attribute
    
    Returns:
        dict: Dictionary of monthly labels in format:
              {"2023-01": {"evidence": "Yes", "categories": [...], "reason": "..."}}
              Returns empty dict if no file exists or on error
    
    File Naming Convention: patient_{patient_id}_monthly_labels.json
    """
    # Safety check - ensure we have a current patient loaded
    if app.current_patient_id is None:
        print("WARNING: No patient ID set for loading labels")
        return {}
    
    # Generate filename based on current patient ID
    # ========== CHANGED: Get group-specific save directory ==========
    save_dir = get_save_directory(app)
    save_file = os.path.join(save_dir, f'patient_{app.current_patient_id}_monthly_labels.json')
    full_path = os.path.abspath(save_file)

    print(f"\n=== LOAD MONTHLY LABELS ===")
    print(f"Looking for file: {full_path}")
    print(f"Group Name: {app.group_name}")
    print(f"Save Directory: {save_dir}")
    print(f"Looking for file: {full_path}")
    print(f"File exists: {os.path.exists(save_file)}")
    
    # Check if labels file exists for this patient
    if os.path.exists(save_file):
        try:
            # Load and parse JSON data
            with open(save_file, 'r') as f:
                data = json.load(f)
            
            # Now that we have data, let's print debug info
            print(f"Type of data: {type(data)}")
            print(f"Loaded {len(data)} monthly labels successfully")
            
            if data:
                print(f"Label months: {list(data.keys())}")
                # Show first label as example
                first_key = list(data.keys())[0]
                print(f"Example label ({first_key}): {data[first_key]}")
            
            print("============================\n")
            return data
            
        except Exception as e:
            # Handle file corruption, permission errors, etc.
            print(f"Error loading monthly labels: {e}")
            import traceback
            traceback.print_exc()
            print("============================\n")
            return {}
    else:
        print("No saved monthly labels file found (this is normal for new patients)")
        print("============================\n")
        return {}
    
    # This line should never be reached, but just in case
    return {}

def save_monthly_labels(app, labels):
    """
    Save monthly labels dictionary to JSON file for the current patient.
    """
    # Safety check - ensure we have a current patient
    if app.current_patient_id is None:
        print("ERROR: No patient ID set - cannot save")
        return
    
    try:
        # ========== CHANGED: Get group-specific save directory ==========
        save_dir = get_save_directory(app)
        save_file = os.path.join(save_dir, f'patient_{app.current_patient_id}_monthly_labels.json')
        full_path = os.path.abspath(save_file)
        
        print(f"\n{'='*50}")
        print(f"SAVE MONTHLY LABELS TO FILE")
        print(f"{'='*50}")
        print(f"Timestamp: {pd.Timestamp.now()}")
        print(f"Patient ID: {app.current_patient_id}")
        print(f"Group Name: {app.group_name}")
        print(f"Save Directory: {save_dir}")
        print(f"Save Path: {full_path}")
        print(f"Number of labels to save: {len(labels)}")
        print(f"Labels data: {json.dumps(labels, indent=2)}")
        
        # Write labels to file with pretty formatting (indent=2)
        with open(save_file, 'w') as f:
            json.dump(labels, f, indent=2)
            
        # Verify the save
        if os.path.exists(save_file):
            file_size = os.path.getsize(save_file)
            print(f"✓ Save successful! File size: {file_size} bytes")
            
            # Try to read it back
            with open(save_file, 'r') as f:
                verify_data = json.load(f)
                print(f"✓ Verification read successful: {len(verify_data)} labels")
        else:
            print("✗ ERROR: File doesn't exist after save attempt!")
        print(f"{'='*50}\n")    
            
    except Exception as e:
        print(f"\n{'!'*50}")
        print(f"ERROR in save_monthly_labels: {e}")
        print(f"Error Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print(f"{'!'*50}\n")
#########

def get_monthly_labels_info(app):
    """
    Generate a formatted string summary of all monthly labels for display.
    
    This function creates a human-readable summary of all saved flare labels
    for the current patient. It's used to populate the "Saved Labels" text
    area in the UI, giving doctors a quick overview of their assessments.
    
    Args:
        app: PatientTimelineApp instance containing current patient context
    
    Returns:
        str: Multi-line formatted string with one line per labeled month
             Example: "January 2023: Yes (Lab Test, Prescription) - High CRP levels"
             Returns "No labels saved yet" if no labels exist
    
    Format Per Line:
        - Month Year: Evidence (Categories) - Reason
        - Categories only shown if evidence="Yes"
        - Reason only shown if provided
    """
    # Load all labels for current patient
    monthly_labels = load_monthly_labels(app)
    
    # Handle case where no labels exist yet
    if not monthly_labels:
        return "No labels saved yet"
    
    info_lines = []
    
    # Mapping from internal category names to user-friendly display names
    # This is the reverse of the mapping used in save_monthly_label()
    label_mapping = {
        'ambulatory_visit': 'Ambulatory Visit',
        'lab_test': 'Lab Test',
        'prescription': 'Prescription', 
        'physician_claim': 'Physician Claim',
        'hospital_admission': 'Hospital Admission',
        'imaging': 'Imaging'
    }
    
    # Process each month's label in chronological order
    for month_period, label_data in sorted(monthly_labels.items()):
        try:
            # Convert period string back to readable month format
            period = pd.Period(month_period)
            month_str = period.strftime('%B %Y')  # "January 2023"
            
            # Extract label components with defaults
            evidence = label_data.get('evidence', 'No')
            
            # Start building the display line
            line = f"{month_str}: {evidence}"
            
            # Add category information if this is a positive flare assessment
            if evidence == "Yes":
                categories = label_data.get('categories', [])
                if categories:
                    # Convert internal names to readable names
                    readable_cats = [label_mapping.get(cat, cat) for cat in categories]
                    line += f" ({', '.join(readable_cats)})"
                
                # Add reason if provided
                reason = label_data.get('reason', '')
                if reason:
                    line += f" - {reason}"
            
            info_lines.append(line)
            
        except Exception as e:
            # Handle individual label formatting errors without breaking entire summary
            print(f"Error formatting label: {e}")
            continue
    
    # Join all lines into a single string for display
    return "\n".join(info_lines)


def get_monthly_labels_list(app):
    """
    Get a list of months that have existing labels for the edit dropdown.
    
    This function generates a list of month strings for populating the
    "Select Month to Edit" dropdown. It only includes months that already
    have labels, making it easy for doctors to find and edit existing assessments.
    
    Args:
        app: PatientTimelineApp instance containing current patient context
    
    Returns:
        list: List of month strings in "January 2023" format
              Returns empty list if no labels exist
              Sorted chronologically (oldest first)
    
    Used By: Edit dropdown in the labelling interface
    """
    # Load existing labels
    monthly_labels = load_monthly_labels(app)
    
    # Return empty list if no labels exist
    if not monthly_labels:
        return []
    
    month_list = []
    
    # Convert each month period to readable format
    for month_period_str in sorted(monthly_labels.keys()):
        try:
            # Parse period string and format for display
            period = pd.Period(month_period_str)
            month_str = period.strftime('%B %Y')
            month_list.append(month_str)
            
        except Exception as e:
            # Skip invalid period entries without breaking the entire list
            print(f"Error formatting month: {e}")
            continue
    
    return month_list


def load_label_for_edit(app, edit_month):
    """
    Load an existing monthly label's data for editing in the form.
    
    This function retrieves a specific month's label data and formats it
    for display in the editing form. It converts internal category names
    back to user-friendly names and populates all form fields.
    
    Args:
        app: PatientTimelineApp instance containing current patient context
        edit_month (str): Month in "January 2023" format to load for editing
    
    Returns:
        tuple: (evidence, readable_categories, reason, status_message)
            - evidence (str): "Yes" or "No"
            - readable_categories (list): User-friendly category names
            - reason (str): Reason text or empty string
            - status_message (str): Success or error message for user feedback
    
    Used By: "Load for Edit" button in the labelling interface
    """
    # Input validation
    if not edit_month:
        return "No", [], "", "Please select a month to edit"
    
    try:
        # Convert month string to period for lookup
        selected_period = pd.to_datetime(edit_month, format='%B %Y').to_period('M')
        monthly_labels = load_monthly_labels(app)
        
        # Check if label exists for this month
        if str(selected_period) in monthly_labels:
            # Extract label data with safe defaults
            label_data = monthly_labels[str(selected_period)]
            evidence = label_data.get('evidence', 'No')
            categories = label_data.get('categories', [])
            reason = label_data.get('reason', '')
            
            # Convert internal category names to readable names for form display
            # This is the reverse mapping of what's used in save_monthly_label()
            internal_to_label = {
                'ambulatory_visit': 'Ambulatory Visit',
                'lab_test': 'Lab Test',
                'prescription': 'Prescription',
                'physician_claim': 'Physician Claim',
                'hospital_admission': 'Hospital Admission',
                'imaging': 'Imaging'
            }
            
            # Convert categories, handling any unknown categories gracefully
            readable_categories = [
                internal_to_label.get(cat, cat.replace('_', ' ').title()) 
                for cat in categories
            ]
            
            return evidence, readable_categories, reason, f"Loaded label for {edit_month}"
        else:
            # No label exists for this month
            return "No", [], "", f"No label found for {edit_month}"
            
    except Exception as e:
        # Handle date parsing or other errors
        return "No", [], "", f"Failed to load label: {str(e)}"


def delete_monthly_label(app, edit_month):
    """
    Permanently delete a monthly label for the specified month.
    
    This function removes a label entry from the patient's data and updates
    the persistent storage. Unlike clear_monthly_label(), this is specifically
    designed for the edit interface and includes additional safety checks.
    
    Args:
        app: PatientTimelineApp instance containing current patient context
        edit_month (str): Month in "January 2023" format to delete
    
    Returns:
        tuple: (status_message, updated_labels_info_string)
            - status_message: Confirmation or error message
            - updated_labels_info_string: Updated summary of remaining labels
    
    Safety Features:
        - Validates month selection
        - Handles non-existent labels gracefully
        - Updates persistent storage immediately
        - Provides clear user feedback
    """
    # Input validation
    if not edit_month:
        return "Please select a month to delete", ""
    
    try:
        # Convert month to period for lookup
        selected_period = pd.to_datetime(edit_month, format='%B %Y').to_period('M')
        monthly_labels = load_monthly_labels(app)
        
        # Check if label exists before attempting deletion
        if str(selected_period) in monthly_labels:
            # Remove the label entry
            del monthly_labels[str(selected_period)]
            
            # Save updated labels to persistent storage
            save_monthly_labels(app, monthly_labels)
            
            # Generate updated summary for UI
            labels_info = get_monthly_labels_info(app)
            return f"Label deleted for {edit_month}", labels_info
        else:
            # Label doesn't exist - still return current labels info
            return f"No label found for {edit_month}", get_monthly_labels_info(app)
            
    except Exception as e:
        # Handle errors and still return current labels info for consistency
        return f"Failed to delete label: {str(e)}", get_monthly_labels_info(app)


# ============================================================================
# CLASS METHOD INJECTION SYSTEM
# ============================================================================
# This section dynamically adds all the monthly labelling functions as methods
# to the PatientTimelineApp class. This approach maintains clean separation
# between the core app functionality and the labelling features while allowing
# the labelling functions to access app state (current_patient_id, etc.)

def add_monthly_labelling_methods(app_class):
    """
    Dynamically add monthly labelling methods to the PatientTimelineApp class.
    
    This function uses Python's dynamic method injection to add all the
    monthly labelling functionality to the main app class. This approach:
    
    1. Keeps the labelling code modular and separate
    2. Allows labelling functions to access app instance state
    3. Maintains clean import structure in the main application
    4. Enables easy testing of labelling functions in isolation
    
    Args:
        app_class (class): The PatientTimelineApp class to extend
    
    Method Naming Convention:
        - External functions: snake_case (e.g., save_monthly_label)
        - Injected methods: same name with _method suffix during injection
        - Final methods: original snake_case name on the class
    
    Usage: Called once during app initialization in main.py
    """
    
    # Define wrapper methods that pass 'self' as the 'app' parameter
    # This allows the external functions to access instance attributes
    # while maintaining their functional interface
    
    def save_monthly_label_method(self, selected_month, evidence, categories, reason):
        """Instance method wrapper for save_monthly_label function"""
        return save_monthly_label(self, selected_month, evidence, categories, reason)
    
    def clear_monthly_label_method(self, selected_month):
        """Instance method wrapper for clear_monthly_label function"""
        return clear_monthly_label(self, selected_month)
    
    def load_monthly_labels_method(self):
        """Instance method wrapper for load_monthly_labels function"""
        return load_monthly_labels(self)
    
    def save_monthly_labels_method(self, labels):
        """Instance method wrapper for save_monthly_labels function"""
        return save_monthly_labels(self, labels)
    
    def get_monthly_labels_info_method(self):
        """Instance method wrapper for get_monthly_labels_info function"""
        return get_monthly_labels_info(self)
    
    def get_monthly_labels_list_method(self):
        """Instance method wrapper for get_monthly_labels_list function"""
        return get_monthly_labels_list(self)
    
    def load_label_for_edit_method(self, edit_month):
        """Instance method wrapper for load_label_for_edit function"""
        return load_label_for_edit(self, edit_month)
    
    def delete_monthly_label_method(self, edit_month):
        """Instance method wrapper for delete_monthly_label function"""
        return delete_monthly_label(self, edit_month)
    
    # Inject all methods into the class
    # These become regular instance methods that can be called as app.method_name()
    app_class.save_monthly_label = save_monthly_label_method
    app_class.clear_monthly_label = clear_monthly_label_method
    app_class.load_monthly_labels = load_monthly_labels_method
    app_class.save_monthly_labels = save_monthly_labels_method
    app_class.get_monthly_labels_info = get_monthly_labels_info_method
    app_class.get_monthly_labels_list = get_monthly_labels_list_method
    app_class.load_label_for_edit = load_label_for_edit_method
    app_class.delete_monthly_label = delete_monthly_label_method