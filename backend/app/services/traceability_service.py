"""
Traceability Matrix Service
Generates comprehensive application-to-infrastructure mappings with rationalization actions
"""

from app.models.industry_data import IndustryData
from app.models.corent_data import CorentData
from app.models.cast import CASTData


class TraceabilityService:
    """Service for generating traceability matrix with action recommendations"""

    @staticmethod
    def get_traceability_matrix():
        """
        Generate complete traceability matrix with all 195 applications
        mapped to infrastructure, repositories, and capabilities
        
        Returns:
            dict with traceability data and summary statistics
        """
        from app import db
        
        # Get all applications with their data
        industry_apps = db.session.query(
            IndustryData.app_id,
            IndustryData.app_name,
            IndustryData.platform_host,
            IndustryData.application_type,
            IndustryData.capabilities
        ).all()
        
        # Get CAST data for repositories
        cast_data = {item.app_id: item for item in db.session.query(CASTData).all()}
        
        # Get CorentData for additional infrastructure info
        corent_data = {item.app_id: item for item in db.session.query(CorentData).all()}
        
        # Build capability groups to determine redundancy
        capability_groups = {}
        for app in industry_apps:
            if app.capabilities:
                caps = [c.strip() for c in str(app.capabilities).split(',') if c.strip()]
                for cap in caps:
                    if cap not in capability_groups:
                        capability_groups[cap] = []
                    capability_groups[cap].append(app.app_id)
        
        # Generate traceability entries
        traceability_matrix = []
        
        for app in industry_apps:
            # Get infrastructure info
            infrastructure = app.platform_host or 'Unknown'
            
            # Get repository info
            cast_item = cast_data.get(app.app_id)
            repository = f"repo/{app.app_id}" if cast_item else 'N/A'
            
            # Get first capability (for main entry)
            if app.capabilities:
                caps = [c.strip() for c in str(app.capabilities).split(',') if c.strip()]
                
                for capability in caps:
                    # Determine redundancy level
                    apps_with_cap = len(capability_groups.get(capability, []))
                    
                    if apps_with_cap == 1:
                        redundancy = 'Unique'
                        action = 'Retain'
                    elif apps_with_cap == 2:
                        redundancy = 'Duplicate'
                        action = 'Migrate to SAP'
                    else:
                        redundancy = 'High'
                        action = 'Decommission' if apps_with_cap > 3 else 'Migrate to SAP'
                    
                    traceability_matrix.append({
                        'app_id': app.app_id,
                        'infrastructure': infrastructure,
                        'application': app.app_name,
                        'repository': repository,
                        'capability': capability,
                        'application_type': app.application_type or 'Unknown',
                        'redundancy': redundancy,
                        'action': action,
                        'apps_with_capability': apps_with_cap
                    })
            else:
                # Apps without capabilities
                traceability_matrix.append({
                    'app_id': app.app_id,
                    'infrastructure': infrastructure,
                    'application': app.app_name,
                    'repository': repository,
                    'capability': 'Unclassified',
                    'application_type': app.application_type or 'Unknown',
                    'redundancy': 'Unique',
                    'action': 'Retain',
                    'apps_with_capability': 1
                })
        
        # Calculate summary statistics
        retain_count = len([item for item in traceability_matrix if item['action'] == 'Retain'])
        migrate_count = len([item for item in traceability_matrix if item['action'] == 'Migrate to SAP'])
        decommission_count = len([item for item in traceability_matrix if item['action'] == 'Decommission'])
        
        # Calculate unique infrastructure and capabilities
        unique_infrastructure = len(set(item['infrastructure'] for item in traceability_matrix))
        unique_capabilities = len(set(item['capability'] for item in traceability_matrix))
        
        # Calculate consolidation savings
        duplicate_entries = [item for item in traceability_matrix if item['redundancy'] in ['Duplicate', 'High']]
        potential_consolidation = len(set(item['app_id'] for item in duplicate_entries))
        
        return {
            'matrix': traceability_matrix,
            'summary': {
                'total_applications': len(industry_apps),
                'total_entries': len(traceability_matrix),
                'unique_infrastructure': unique_infrastructure,
                'unique_capabilities': unique_capabilities,
                'applications_to_retain': retain_count,
                'applications_to_migrate': migrate_count,
                'applications_to_decommission': decommission_count,
                'potential_consolidation': potential_consolidation,
                'consolidation_ratio': f"{potential_consolidation}:{unique_capabilities}"
            }
        }
