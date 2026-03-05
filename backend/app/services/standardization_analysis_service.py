"""
Standardization & Consolidation Analysis Service
Analyzes CORENT and CAST data to generate business recommendations
"""

import pandas as pd
from typing import Dict, List, Any
from app import db, create_app
from app.models.corent_data import CorentData
from app.models.cast import CASTData


class StandardizationAnalysisService:
    """Generate standardization and consolidation recommendations based on real data"""
    
    @staticmethod
    def analyze_all_data() -> Dict[str, Any]:
        """Comprehensive analysis of CORENT and CAST data"""
        
        corent = db.session.query(CorentData).all()
        cast = db.session.query(CASTData).all()
        
        return {
            'infrastructure_analysis': StandardizationAnalysisService._analyze_infrastructure(corent),
            'code_analysis': StandardizationAnalysisService._analyze_code(cast),
            'consolidation_opportunities': StandardizationAnalysisService._identify_consolidation_opportunities(corent, cast),
            'technology_standardization': StandardizationAnalysisService._analyze_technology_stack(corent, cast),
            'business_value_recommendations': StandardizationAnalysisService._generate_business_recommendations(corent, cast),
            'roi_analysis': StandardizationAnalysisService._calculate_roi_impact(corent, cast),
            'risk_assessment': StandardizationAnalysisService._assess_consolidation_risks(corent, cast)
        }
    
    @staticmethod
    def _analyze_infrastructure(corent_items: List) -> Dict[str, Any]:
        """Analyze infrastructure landscape"""
        
        # Server distribution
        platform_hosts = {}
        for item in corent_items:
            if item.platform_host:
                host = item.platform_host
                if host not in platform_hosts:
                    platform_hosts[host] = {'apps': [], 'environments': [], 'stability': []}
                platform_hosts[host]['apps'].append(item.app_id)
                env = item.environment or 'Unknown'
                if env not in platform_hosts[host]['environments']:
                    platform_hosts[host]['environments'].append(env)
                platform_hosts[host]['stability'].append(item.application_stability or 'Unknown')
        
        # Environment distribution
        environments = {}
        for item in corent_items:
            env = item.environment or 'Unknown'
            if env not in environments:
                environments[env] = []
            environments[env].append(item.app_id)
        
        # Cloud suitability
        cloud_suitability = {}
        for item in corent_items:
            suit = item.cloud_suitability or 'Unknown'
            if suit not in cloud_suitability:
                cloud_suitability[suit] = []
            cloud_suitability[suit].append(item.app_id)
        
        return {
            'total_applications': len(corent_items),
            'total_servers': len(platform_hosts),
            'unique_servers': len(platform_hosts),
            'top_servers': sorted(platform_hosts.items(), key=lambda x: len(x[1]['apps']), reverse=True)[:10],
            'environment_distribution': {env: len(apps) for env, apps in environments.items()},
            'cloud_readiness': {suit: len(apps) for suit, apps in cloud_suitability.items()},
            'multi_environment_apps': len(corent_items)
        }
    
    @staticmethod
    def _analyze_code(cast_items: List) -> Dict[str, Any]:
        """Analyze code quality and architecture"""
        
        # Code availability
        with_source = len([c for c in cast_items if c.source_code_availability == 'Yes'])
        without_source = len([c for c in cast_items if c.source_code_availability == 'No'])
        
        # Programming languages
        languages = {}
        for item in cast_items:
            if item.programming_language:
                langs = [l.strip() for l in str(item.programming_language).split(',')]
                for lang in langs:
                    languages[lang] = languages.get(lang, 0) + 1
        
        # Architecture types
        architectures = {}
        for item in cast_items:
            if item.application_architecture:
                arch = item.application_architecture
                architectures[arch] = architectures.get(arch, 0) + 1
        
        # Cloud suitability from CAST
        cloud_ready = len([c for c in cast_items if c.cloud_suitability in ['High', 'Cloud Native', 'Cloud Optimized']])
        
        return {
            'total_with_source_code': with_source,
            'total_without_source_code': without_source,
            'source_code_availability': f"{(with_source / len(cast_items) * 100):.1f}%",
            'top_languages': dict(sorted(languages.items(), key=lambda x: -x[1])[:10]),
            'architecture_distribution': architectures,
            'cloud_ready_apps': cloud_ready,
            'cloud_readiness_percentage': f"{(cloud_ready / len(cast_items) * 100):.1f}%"
        }
    
    @staticmethod
    def _identify_consolidation_opportunities(corent_items: List, cast_items: List) -> List[Dict[str, Any]]:
        """Identify applications that can be consolidated"""
        
        opportunities = []
        
        # Group by platform host
        by_platform = {}
        for item in corent_items:
            host = item.platform_host or 'Unknown'
            if host not in by_platform:
                by_platform[host] = []
            by_platform[host].append(item)
        
        # Identify consolidation targets
        for platform, apps in by_platform.items():
            if len(apps) >= 3:  # Platform with multiple apps
                # Check stability
                stable_apps = [a for a in apps if a.application_stability in ['Stable', 'Good']]
                unstable_apps = [a for a in apps if a.application_stability in ['Unstable', 'Poor']]
                
                if unstable_apps and stable_apps:
                    opportunities.append({
                        'platform': platform,
                        'total_apps': len(apps),
                        'stable_apps': len(stable_apps),
                        'unstable_apps': len(unstable_apps),
                        'potential_consolidation': len(unstable_apps),
                        'reason': 'Consolidate unstable applications onto stable platform',
                        'apps_to_consolidate': [a.app_id for a in unstable_apps],
                        'target_platform': [a.app_id for a in stable_apps][:1]
                    })
        
        return sorted(opportunities, key=lambda x: x['potential_consolidation'], reverse=True)[:5]
    
    @staticmethod
    def _analyze_technology_stack(corent_items: List, cast_items: List) -> Dict[str, Any]:
        """Analyze technology standardization opportunities"""
        
        # Operating systems
        os_dist = {}
        for item in corent_items:
            if item.operating_system:
                os = item.operating_system
                os_dist[os] = os_dist.get(os, 0) + 1
        
        # Databases
        db_dist = {}
        for item in corent_items:
            if item.db_engine and item.db_engine != 'Not Applicable':
                db = item.db_engine
                db_dist[db] = db_dist.get(db, 0) + 1
        
        # Server types
        server_type_dist = {}
        for item in corent_items:
            if item.server_type:
                st = item.server_type
                server_type_dist[st] = server_type_dist.get(st, 0) + 1
        
        return {
            'operating_systems': dict(sorted(os_dist.items(), key=lambda x: -x[1])[:5]),
            'database_engines': dict(sorted(db_dist.items(), key=lambda x: -x[1])[:5]),
            'server_types': dict(sorted(server_type_dist.items(), key=lambda x: -x[1])[:5]),
            'standardization_potential': len([item for item in corent_items if item.cloud_suitability in ['High', 'Medium']])
        }
    
    @staticmethod
    def _generate_business_recommendations(corent_items: List, cast_items: List) -> List[Dict[str, Any]]:
        """Generate business-value-focused recommendations"""
        
        recommendations = []
        
        # 1. Cloud Migration Priority
        cloud_ready_apps = [c for c in corent_items if c.cloud_suitability == 'High']
        if len(cloud_ready_apps) > 0:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Cloud Migration',
                'title': 'Migrate High-Readiness Applications to Cloud First',
                'value_proposition': f'{len(cloud_ready_apps)} applications are already cloud-ready (High suitability)',
                'business_impact': 'Reduces on-premise infrastructure costs, improves scalability and elasticity',
                'apps_affected': len(cloud_ready_apps),
                'estimated_savings': f'EUR {len(cloud_ready_apps) * 15000}/year in infrastructure',
                'timeline': '6-12 months',
                'apps_list': [a.app_id for a in cloud_ready_apps][:5]
            })
        
        # 2. Legacy Application Modernization
        legacy_apps = [c for c in corent_items if c.cloud_suitability in ['Low', 'Not Suitable']]
        if len(legacy_apps) > 0:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Modernization',
                'title': 'Prioritize Modernization of Legacy Applications',
                'value_proposition': f'{len(legacy_apps)} applications have low/no cloud suitability - modernization needed',
                'business_impact': 'Enables future cloud migration, reduces technical debt, improves maintainability',
                'apps_affected': len(legacy_apps),
                'estimated_savings': f'EUR {len(legacy_apps) * 8000}/year in reduced maintenance',
                'timeline': '18-24 months',
                'apps_list': [a.app_id for a in legacy_apps][:5]
            })
        
        # 3. Database Consolidation
        distinct_dbs = len([item for item in corent_items if item.db_engine and item.db_engine != 'Not Applicable'])
        if distinct_dbs > 3:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Database Consolidation',
                'title': f'Consolidate {distinct_dbs} Database Technologies to 3-4 Standard Platforms',
                'value_proposition': f'Multiple database engines create complexity and support overhead',
                'business_impact': 'Standardization reduces operational complexity, improves automation potential',
                'apps_affected': distinct_dbs,
                'estimated_savings': f'EUR {distinct_dbs * 12000}/year in DBA support and licensing',
                'timeline': '12-18 months',
                'recommended_target': 'PostgreSQL, Oracle, MySQL - based on application requirements'
            })
        
        # 4. OS Standardization
        distinct_os = len([item for item in corent_items if item.operating_system])
        if distinct_os > 4:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'OS Standardization',
                'title': f'Standardize Operating Systems ({distinct_os} current variants)',
                'value_proposition': 'Multiple OS platforms increase operational complexity',
                'business_impact': 'Reduces training needs, improves patch management, enhances security posture',
                'apps_affected': distinct_os,
                'estimated_savings': f'EUR {distinct_os * 8000}/year in consolidated management',
                'timeline': '12-15 months',
                'recommended_target': 'RHEL/CentOS for Linux, Windows Server LTS for Windows workloads'
            })
        
        # 5. Stable Infrastructure Consolidation
        stable_apps = [c for c in corent_items if c.application_stability == 'Stable']
        unstable_apps = [c for c in corent_items if c.application_stability in ['Unstable', 'Poor']]
        if len(unstable_apps) > 5:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Infrastructure Optimization',
                'title': f'Consolidate {len(unstable_apps)} Unstable Applications',
                'value_proposition': f'{len(unstable_apps)} applications have stability issues requiring migration',
                'business_impact': 'Improves system reliability, reduces downtime, enhances user experience',
                'apps_affected': len(unstable_apps),
                'estimated_savings': f'EUR {len(unstable_apps) * 5000}/year in reduced incident management',
                'timeline': '9-12 months',
                'apps_list': [a.app_id for a in unstable_apps][:5]
            })
        
        # 6. Code Quality Improvements
        with_source = len([c for c in cast_items if c.source_code_availability == 'Yes'])
        modernizable = len([c for c in cast_items if c.cloud_suitability in ['Medium', 'High']])
        if with_source > 100:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Code Quality',
                'title': f'{with_source} Applications Ready for Code Modernization',
                'value_proposition': f'{with_source} applications have source code available - ready for refactoring',
                'business_impact': 'Reduces technical debt, improves code maintainability, enables faster feature delivery',
                'apps_affected': with_source,
                'estimated_savings': f'EUR {with_source * 3000}/year in improved productivity',
                'timeline': 'Ongoing (phased approach)',
                'apps_list': [c.app_id for c in cast_items if c.source_code_availability == 'Yes'][:5]
            })
        
        # 7. Infrastructure Consolidation - On-Premise
        on_prem_apps = len([c for c in corent_items if c.install_type in ['On Premise', 'On-Prem']])
        if on_prem_apps > 50:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Infrastructure Consolidation',
                'title': f'Consolidate {on_prem_apps} On-Premise Applications',
                'value_proposition': f'{on_prem_apps} applications running on-premise represent ongoing capex/opex',
                'business_impact': 'Reduces physical infrastructure footprint, improves space utilization',
                'apps_affected': on_prem_apps,
                'estimated_savings': f'EUR {on_prem_apps * 2000}/year in datacenter costs',
                'timeline': '18-24 months'
            })
        
        return sorted(recommendations, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(x['priority'], 3))
    
    @staticmethod
    def _calculate_roi_impact(corent_items: List, cast_items: List) -> Dict[str, Any]:
        """Calculate ROI for standardization and consolidation"""
        
        # Current state costs
        total_apps = len(corent_items)
        distinct_platforms = len(set(c.platform_host for c in corent_items if c.platform_host))
        
        # Estimated current annual costs
        infrastructure_cost = total_apps * 5000  # EUR 5K per app/year
        management_cost = distinct_platforms * 20000  # EUR 20K per platform/year
        license_cost = total_apps * 2000  # EUR 2K per app/year
        current_total = infrastructure_cost + management_cost + license_cost
        
        # Post-standardization costs
        target_platforms = 5  # Consolidate to 5 platforms
        target_cost_per_app = 3500  # EUR 3.5K after optimization
        post_management = target_platforms * 15000  # EUR 15K per optimized platform
        post_license = total_apps * 1500  # EUR 1.5K (better licensing through standardization)
        post_total = (total_apps * target_cost_per_app) + post_management + post_license
        
        # Calculate savings
        annual_savings = current_total - post_total
        implementation_cost = total_apps * 8000  # EUR 8K per app for migration
        payback_period = implementation_cost / max(annual_savings, 1)  # In years
        five_year_roi = (annual_savings * 5) - implementation_cost
        
        return {
            'current_annual_cost': f'EUR {current_total:,}',
            'infrastructure_cost': f'EUR {infrastructure_cost:,}',
            'management_cost': f'EUR {management_cost:,}',
            'license_cost': f'EUR {license_cost:,}',
            'post_standardization_cost': f'EUR {post_total:,}',
            'annual_savings': f'EUR {annual_savings:,}',
            'implementation_cost': f'EUR {implementation_cost:,}',
            'payback_period_years': f'{payback_period:.1f}',
            'five_year_roi': f'EUR {five_year_roi:,}',
            'roi_percentage': f'{((five_year_roi / implementation_cost) * 100):.0f}%'
        }
    
    @staticmethod
    def _assess_consolidation_risks(corent_items: List, cast_items: List) -> List[Dict[str, Any]]:
        """Assess risks of standardization and consolidation"""
        
        risks = []
        
        # High-risk applications (unstable, complex)
        high_risk_apps = [c for c in corent_items if c.application_stability == 'Unstable']
        if len(high_risk_apps) > 0:
            risks.append({
                'level': 'HIGH',
                'category': 'Application Stability',
                'description': f'{len(high_risk_apps)} unstable applications could cause integration delays',
                'mitigation': 'Stabilize applications before consolidation or plan parallel systems',
                'apps_affected': len(high_risk_apps)
            })
        
        # Complex dependency apps
        high_dependency_apps = [c for c in corent_items if (isinstance(c.volume_external_dependencies, str) and 
                                int(c.volume_external_dependencies) > 15 if c.volume_external_dependencies else False) or
                               (isinstance(c.volume_external_dependencies, int) and c.volume_external_dependencies > 15)]
        if len(high_dependency_apps) > 0:
            risks.append({
                'level': 'MEDIUM',
                'category': 'Data Integration Complexity',
                'description': f'{len(high_dependency_apps)} applications have high external dependencies',
                'mitigation': 'Map all dependencies before consolidation, plan integration testing',
                'apps_affected': len(high_dependency_apps)
            })
        
        # Legacy systems
        legacy_apps = [c for c in corent_items if c.cloud_suitability == 'Not Suitable']
        if len(legacy_apps) > 0:
            risks.append({
                'level': 'MEDIUM',
                'category': 'Legacy System Integration',
                'description': f'{len(legacy_apps)} legacy systems may not easily integrate',
                'mitigation': 'Plan anti-corruption layers, consider strangler pattern for migration',
                'apps_affected': len(legacy_apps)
            })
        
        # No source code apps
        no_source_apps = len([c for c in cast_items if c.source_code_availability == 'No'])
        if no_source_apps > 0:
            risks.append({
                'level': 'MEDIUM',
                'category': 'Code Modernization Risk',
                'description': f'{no_source_apps} applications have no source code available',
                'mitigation': 'Prioritize applications with source code, acquire source for critical apps if possible',
                'apps_affected': no_source_apps
            })
        
        return sorted(risks, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(x['level'], 3))
