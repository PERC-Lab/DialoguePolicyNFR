import os
import json

def get_all_requirements():
    """
    Parse All_NFRs.txt and return requirements in the same format as server.py.
    Returns a list of lists, where each inner list contains at most 10 NFRs.
    Each NFR has: id, title, description
    """
    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    nfr_file = os.path.join(current_dir, 'All_NFRs.txt')
    
    requirements = []
    current_section = None
    requirement_id = 1
    current_page = []
    
    with open(nfr_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a section header (starts with §)
            if line.startswith('§'):
                # Remove trailing period if present
                current_section = line.rstrip('.')
            # Check if this is a requirement (starts with "The system" or "*The system")
            elif line.startswith('The system') or line.startswith('*The system'):
                # Remove leading asterisk if present
                description = line.lstrip('*')
                # Create requirement object
                requirement = {
                    "id": requirement_id,
                    "title": current_section if current_section else "Unknown Section",
                    "description": description
                }
                
                # Add to current page
                current_page.append(requirement)
                requirement_id += 1
                
                # If page has 10 items, start a new page
                if len(current_page) >= 10:
                    requirements.append(current_page)
                    current_page = []
    
    # Add the last page if it has items
    if current_page:
        requirements.append(current_page)
    
    return requirements


def get_requirements_by_batch(batch=1):
    start_index = (batch-1)*5
    end_index = start_index + 5
    all_requirements = get_all_requirements()[start_index:end_index]
    return all_requirements




requirements = get_all_requirements()
import json


json_file = 'requirements.json'

with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(requirements, f, ensure_ascii=False, indent=4)
