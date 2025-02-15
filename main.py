import datetime
import requests
import json
import re
from typing import Dict, Tuple

def create_hipaa_prompt() -> str:
    """Creates a detailed prompt for the LLM to identify HIPAA PHI elements."""
    return f'''You are a HIPAA compliance expert. Analyze the text provided at the end and identify all HIPAA Safe Harbor PHI elements including:
    - Names related to patient (including full names, first names, last names)
    - Addresses or geographic subdivisions smaller than state (street locations, clinic/hospital names, etc)
    - Dates (except years) and DOBs related to individuals
    - Ages over 89
    - Phone numbers
    - Fax numbers
    - Email addresses
    - Social Security numbers
    - Medical record numbers
    - Health plan beneficiary
    - Account numbers
    - Certificate/license numbers
    - Vehicle identifiers (VIN, license plates)
    - Device identifiers and serial numbers
    - URLs
    - IP addresses
    - Biometric identifiers
    - Full-face photos or comparable images
    - Other unique identifiable numbers such as NPIs, policy numbers, etc.

Do not remove data if it not in the above list.
Also, it is okay to keep physician/provider names.

Return a JSON object where:
- Each key is the exact PHI text found
- Each value is a standardized variable name indicating the type of PHI
Example: {{
  "John A. Smith": "NAME_1", 
  "123 Main St, Chicago, IL 60601": "ADDRESS_1", 
  "09/28/1975": "DOB_1", 
  "(312) 555-1234": "PHONE_1", 
  "(312) 555-5678": "FAX_1", 
  "john.smith@email.com": "EMAIL_1", 
  "123-45-6789": "SSN_1", 
  "ABC123XYZ": "MEDICAL_RECORD_1", 
  "XYZ-987654321": "HEALTH_PLAN_BENEFICIARY_1", 
  "1234567890": "ACCOUNT_NUMBER_1", 
  "XYZ-987654": "CERTIFICATE_LICENSE_1", 
  "1HGBH41JXMN109186": "VEHICLE_ID_1", 
  "device123456": "DEVICE_ID_1", 
  "aeiou12345": "WEB_URL_1", 
  "192.168.1.1": "IP_ADDRESS_1", 
  "123456": "BIOMETRIC_ID_1", 
  "patient_photo.jpg": "PHOTO_ID_1", 
  "Patient #789 in Study ABC": "UNIQUE_IDENTIFIER_1", 
  "5647382910": "NPI_1", 
  "Cedars-Sinai Medical Center": "HOSPITAL_1" 
}}

Only include EXACT matches found in the text. Do not make assumptions or include elements not present. Do not make up data. 

If there is no text or PHI simply return "no PHI".'''

def call_ollama(text: str, prompt: str, model: str = "mistral-small:24b", temperature: float = 0.2) -> Dict[str, str]:
    """
    Calls Ollama API with the given text and prompt.
    Returns a dictionary of PHI mappings.
    """
    try:
        full_prompt = f"{prompt}\n\nText to analyze:\n{text}"
        # print(full_prompt)
        response = requests.post('http://localhost:11434/api/generate',
            json={
                "model": model,
                "options": {
                    "temperature": temperature,
                },
                "prompt": full_prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        
        # Extract the response text
        response_data = response.json()
        # print(response_data)
        response_text = response_data['response']
        print(f"Response Text: {response_text}")
        
        # Parse the JSON response
        # Find the JSON object in the response text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}
        
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return {}
    
def sanitize_text(text: str, complete_phi_mappings: dict) -> str:
    deidentified_text = text
    for phi, replacement in complete_phi_mappings.items():
        deidentified_text = deidentified_text.replace(phi, f"[{replacement}]")
    
    return deidentified_text

def deidentify_text(text: str, complete_phi_mappings: dict):
    """
    Build a chunk of complete_phi_mappings using text and Ollama.
    Updtate complete_phi_mappings with the new mappings.
    """
    # Get the PHI mappings from Ollama
    prompt = create_hipaa_prompt()
    print(f"Text: {text}", )
    print("\n")
    print(f"Existing PHI Mappings: {complete_phi_mappings}")
    print("\n")
    not_valid = True
    while not_valid:
        phi_mappings = call_ollama(text, prompt)
        print(f"NEW PHI Mappings: {phi_mappings}")
        print("\n")
        # not valid if any key or value in phi_mappings is blank 
        not_valid = any([not value for value in phi_mappings.values()]) or any([not key for key in phi_mappings.keys()])
        if not_valid:
            print("Invalid response. Trying again...")
            continue

        # De-duplicate the mappings
        # If a key already exists in complete_phi_mappings, remove it from phi_mappings
        keys_to_remove = [key for key in phi_mappings if key in complete_phi_mappings]
        for key in keys_to_remove:
            print(f"Removing duplicate key: {key}")
            del phi_mappings[key]

        # if a value already exists in complete_phi_mappings, increment the value by 1 until it is unique
        # for example _1 becomes _2
        for key, value in phi_mappings.items():
            temp_value = value
            while temp_value in complete_phi_mappings.values() or list(phi_mappings.values()).count(temp_value) > 1:
                print(f"temp_value: {temp_value}")
                # if it doesn't end in a number, add _1, else increment the number
                if not re.search(r'_(\d+)$', temp_value):
                    new_value = temp_value + "_1"
                else:
                    new_value = re.sub(r'_(\d+)$', lambda x: f"_{int(x.group(1)) + 1}", temp_value)
                temp_value = new_value
                print(f"new_value: {new_value}")
            phi_mappings[key] = temp_value

    # Update complete_phi_mappings with the new unique mappings
    complete_phi_mappings.update(phi_mappings)

def process_document(text: str, separator: str) -> Tuple[str, Dict[str, str]]:
    """
    Processes a complete document paragraph by paragraph.
    Returns the fully deidentified text and complete PHI mapping dictionary.
    """
    paragraphs = text.split(separator)
    deidentified_paragraphs = []
    complete_phi_mappings = {}
    
    # build mapping first
    for paragraph in paragraphs:
        if paragraph.strip():
            deidentify_text(paragraph, complete_phi_mappings)
    
    # deidentify text with complete mapping
    for paragraph in paragraphs:
        if paragraph.strip():
            deidentified_para = sanitize_text(paragraph, complete_phi_mappings)
            deidentified_paragraphs.append(deidentified_para)
    
    return '\n\n'.join(deidentified_paragraphs), complete_phi_mappings

def main():
    # get test from /patient_charts folder
    # first list filenames
    import os
    patient_charts = os.listdir("patient_charts")
    print("Patient Charts:")
    print("-" * 50)
    # run 5 times for each chart to see how the PHI mappings change/consistency
    for i in range(5):
        for chart_name in patient_charts:
            print(chart_name)
            sample_text = open(f"patient_charts/{chart_name}", encoding='utf-8').read()

            deidentified_text, phi_mappings = process_document(sample_text, '\n---\n')

            # count how many times each PHI element appears in the text
            phi_counts = {phi: len(re.findall(re.escape(phi), deidentified_text)) for phi in phi_mappings.values()}
            
            # write this to files
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            with open(f"outputs/{chart_name}_{timestamp}_deidentified_text.txt", "w") as f:
                f.write(deidentified_text)
            with open(f"outputs/{chart_name}_{timestamp}_phi_mappings.json", "w") as f:
                json.dump(phi_mappings, f, indent=2)
            with open(f"outputs/{chart_name}_{timestamp}_phi_counts.json", "w") as f:
                json.dump(phi_counts, f, indent=2)

if __name__ == "__main__":
    main()