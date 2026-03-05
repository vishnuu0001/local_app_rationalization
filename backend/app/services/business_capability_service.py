"""
Business Capability Mapping Service
Joins CORENT and CAST data to create capability-based application mappings
"""

from sqlalchemy import func, and_
from app.models.corent_data import CorentData
from app.models.cast import ApplicationClassification, CASTData
from app.models.industry_data import IndustryData


class BusinessCapabilityService:
    """Service for creating and analyzing business capability mappings"""

    @staticmethod
    def get_capability_application_mapping(page=1, per_page=10):
        """
        Get paginated application-to-capability mappings
        
        Args:
            page: Page number (1-indexed)
            per_page: Applications per page
            
        Returns:
            dict with paginated data and metadata
        """
        from app import db
        from sqlalchemy.orm import joinedload
        from sqlalchemy import func
        
        corent_count = db.session.query(func.count(CorentData.id)).scalar() or 0

        applications = []
        total_count = 0

        if corent_count > 0:
            query = db.session.query(CorentData).order_by(CorentData.app_name)
            total_count = query.count()
            paginated_apps = query.paginate(page=page, per_page=per_page, error_out=False)

            # Build a lookup of IndustryData by app_id for application_type and capabilities
            industry_map = {}
            industry_rows = db.session.query(
                IndustryData.app_id,
                IndustryData.application_type,
                IndustryData.capabilities
            ).all()
            for row in industry_rows:
                industry_map[row.app_id] = row

            for corent_app in paginated_apps.items:
                industry = industry_map.get(corent_app.app_id)

                # Fall back to ApplicationClassification if IndustryData not available
                if not industry:
                    classification = db.session.query(ApplicationClassification).filter(
                        ApplicationClassification.app_id == corent_app.app_id
                    ).first()
                    app_type = classification.application_type if classification else 'N/A'
                    capability = classification.capabilities if classification else 'Unclassified'
                else:
                    app_type = industry.application_type or 'N/A'
                    capability = industry.capabilities or 'Unclassified'

                applications.append({
                    'app_id': corent_app.app_id,
                    'app_name': corent_app.app_name,
                    'business_owner': corent_app.business_owner or 'Unknown',
                    'architecture_type': corent_app.architecture_type or 'N/A',
                    'platform_host': corent_app.platform_host or 'N/A',
                    'application_type': app_type,
                    'install_type': corent_app.install_type or 'N/A',
                    'capability': capability
                })
        else:
            industry_query = db.session.query(IndustryData).order_by(IndustryData.app_name)
            total_count = industry_query.count()
            paginated_apps = industry_query.paginate(page=page, per_page=per_page, error_out=False)

            for item in paginated_apps.items:
                applications.append({
                    'app_id': item.app_id,
                    'app_name': item.app_name,
                    'business_owner': item.business_owner or 'Unknown',
                    'architecture_type': item.architecture_type or 'N/A',
                    'platform_host': item.platform_host or 'N/A',
                    'application_type': item.application_type or 'N/A',
                    'install_type': item.install_type or 'N/A',
                    'capability': item.capabilities or 'Unclassified'
                })
        
        return {
            'applications': applications,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page,
                'has_next': page < ((total_count + per_page - 1) // per_page),
                'has_prev': page > 1
            }
        }

    @staticmethod
    def get_capability_analysis():
        """
        Analyze applications grouped by capability to identify elimination candidates.
        Gets capabilities from IndustryData and joins with Corent and CAST data.
        
        Returns:
            dict with capability analysis based on actual Industry/Corent/CAST data
        """
        from app import db
        
        # Get all applications with their capabilities from IndustryData
        industry_apps = db.session.query(
            IndustryData.app_id,
            IndustryData.app_name,
            IndustryData.capabilities,
            IndustryData.business_owner,
            IndustryData.application_type
        ).filter(
            IndustryData.capabilities.isnot(None),
            IndustryData.capabilities != ''
        ).all()
        
        # Group by capability
        capability_groups = {}
        for app in industry_apps:
            # Handle comma-separated capabilities
            caps = [c.strip() for c in str(app.capabilities).split(',') if c.strip()]
            for cap in caps:
                if cap not in capability_groups:
                    capability_groups[cap] = []
                capability_groups[cap].append({
                    'app_id': app.app_id,
                    'app_name': app.app_name,
                    'business_owner': app.business_owner or 'Unknown',
                    'application_type': app.application_type or 'N/A'
                })
        
        # Analyze each capability group
        capabilities = []
        total_apps = len(industry_apps)
        elimination_candidates_count = 0
        total_redundant_apps = 0
        
        for capability, apps in sorted(capability_groups.items(), key=lambda x: len(x[1]), reverse=True):
            app_count = len(apps)
            
            # Mark as elimination candidate if multiple apps (2+) share same capability
            is_elimination_candidate = app_count > 1
            if is_elimination_candidate:
                elimination_candidates_count += 1
                total_redundant_apps += max(0, app_count - 1)
            
            # Get sample app
            sample_app = apps[0]['app_name'] if apps else 'Unknown'
            
            # Calculate optimization potential
            optimization_potential = {
                'redundant_apps': max(0, app_count - 1),
                'consolidation_ratio': f'{app_count}:1',
                'target_apps': 1
            }
            
            cap_obj = {
                'capability': capability,
                'app_count': app_count,
                'is_elimination_candidate': is_elimination_candidate,
                'elimination_reason': f'{app_count} applications provide this capability - consolidation opportunity' if is_elimination_candidate else None,
                'sample_app': sample_app,
                'apps': apps,
                'optimization_potential': optimization_potential,
                'priority': 'HIGH' if app_count > 5 else 'MEDIUM' if app_count > 2 else 'LOW'
            }
            
            capabilities.append(cap_obj)
        
        return {
            'summary': {
                'total_capabilities': len(capabilities),
                'total_applications': total_apps,
                'elimination_candidates': elimination_candidates_count,
                'total_redundant_apps': total_redundant_apps,
                'apps_with_shared_capability': elimination_candidates_count
            },
            'capabilities': capabilities
        }

    @staticmethod
    def get_capability_details(capability_name):
        """
        Get all applications for a specific capability with consolidation analysis
        
        Args:
            capability_name: Name of the business capability
            
        Returns:
            dict with capability details and applications (actual data only)
        """
        from app import db
        
        # Query ALL industry apps (no filtering initially)
        ALL_apps = db.session.query(IndustryData).filter(
            IndustryData.capabilities.isnot(None),
            IndustryData.capabilities != ''
        ).all()
        
        # Normalize the search term: strip "(Provides)"/"(Consumes)" suffixes for flexible matching
        search_term = capability_name.lower().replace(' (provides)', '').replace(' (consumes)', '').strip()
        
        # Build applications list - manually iterate and check
        applications = []
        for app in ALL_apps:
            # Get capabilities for this app
            caps_str = str(app.capabilities) if app.capabilities else ""
            caps_lower = caps_str.lower().replace(' (provides)', '').replace(' (consumes)', '')
            
            # Substring match against normalized capabilities
            if search_term in caps_lower or capability_name.lower() in caps_str.lower():
                try:
                    corent_record = db.session.query(CorentData.install_type).filter(
                        CorentData.app_id == app.app_id
                    ).first()
                    install_type = corent_record.install_type if corent_record else 'N/A'
                except:
                    install_type = 'N/A'
                
                applications.append({
                    'app_id': app.app_id,
                    'app_name': app.app_name,
                    'business_owner': app.business_owner or 'Unknown',
                    'architecture_type': app.architecture_type or 'N/A',
                    'platform_host': app.platform_host or 'N/A',
                    'application_type': app.application_type or 'N/A',
                    'install_type': install_type,
                    'technology_stack': app.application_type or 'N/A'
                })
        
        # Build consolidation analysis
        if len(applications) > 1:
            tech_stacks = {}
            for app_dict in applications:
                tech = app_dict['technology_stack']
                if tech not in tech_stacks:
                    tech_stacks[tech] = []
                tech_stacks[tech].append(app_dict['app_name'])
            
            apps_to_consolidate = len(applications)
            apps_to_eliminate = max(1, apps_to_consolidate - 1)
            
            analysis = {
                'total_apps': len(applications),
                'is_elimination_candidate': True,
                'elimination_reason': f'{len(applications)} applications provide this capability',
                'technology_distribution': tech_stacks,
                'consolidation_summary': {
                    'apps_to_consolidate': apps_to_consolidate,
                    'apps_to_eliminate': apps_to_eliminate,
                    'consolidation_ratio': f'{apps_to_consolidate}:1',
                    'recommendation': f'Consolidate {apps_to_consolidate} applications into 1 optimal solution, eliminate {apps_to_eliminate} redundant applications'
                }
            }
        else:
            analysis = {
                'total_apps': len(applications),
                'is_elimination_candidate': False,
                'elimination_reason': None,
                'recommendation': 'Single application - already optimal. No consolidation needed.' if len(applications) == 1 else 'No applications found for this capability.'
            }
        
        return {
            'capability': capability_name,
            'analysis': analysis,
            'applications': applications
        }

    @staticmethod
    def get_capability_mapping_export(format_type='json'):
        """
        Export complete capability mapping for analysis
        
        Args:
            format_type: Export format ('json', 'csv')
            
        Returns:
            dict with exportable data
        """
        from app import db
        
        # Get complete mapping — join CorentData with IndustryData for app_type & capabilities
        query = db.session.query(
            CorentData.app_id,
            CorentData.app_name,
            CorentData.business_owner,
            CorentData.architecture_type,
            CorentData.platform_host,
            IndustryData.application_type,
            CorentData.install_type,
            IndustryData.capabilities
        ).outerjoin(
            IndustryData,
            CorentData.app_id == IndustryData.app_id
        ).order_by(
            IndustryData.capabilities,
            CorentData.app_name
        ).all()
        
        data = []
        for app in query:
            data.append({
                'APP_ID': app.app_id,
                'APP_NAME': app.app_name,
                'BUSINESS_OWNER': app.business_owner or 'Unknown',
                'ARCHITECTURE_TYPE': app.architecture_type or 'N/A',
                'PLATFORM_HOST': app.platform_host or 'N/A',
                'APPLICATION_TYPE': app.application_type or 'N/A',
                'INSTALL_TYPE': app.install_type or 'N/A',
                'BUSINESS_CAPABILITY': app.capabilities or 'Unclassified'
            })
        
        return {
            'format': format_type,
            'total_records': len(data),
            'data': data
        }
